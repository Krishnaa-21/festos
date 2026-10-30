"""FestOS planning engine. Reads the data pack, writes plans + findings to OUT.
Run: python festos_engine.py <pack_dir> <out_dir>
Every assumption is in ASSUME and echoed to assumptions.csv. Nothing is silently defaulted:
blank gender/diet stay UNKNOWN, hard needs are never relaxed, shortages are reported not hidden."""
import sys, os, math, json
import pandas as pd
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/pack'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/mnt/user-data/outputs/festos'
os.makedirs(OUT, exist_ok=True)
rd = lambda f: pd.read_csv(f'{SRC}/{f}.csv', dtype=str, keep_default_na=False)
P, R, E, V, H, X, L, M, VN, T, C = [rd(f) for f in
    ['participants', 'registrations', 'events', 'venues', 'hostels', 'external_stays',
     'inventory_logistics', 'inventory_merch', 'vendors', 'core_team', 'contingents']]
TS = pd.Timestamp
ASSUME = {
    'cleaning_hours_between_occupants': 3,
    'late_night_window': '22:00-06:00 arrival or departure needs transport=yes',
    'minor_age_below': 18,
    'setup_teardown_min_each_side': 15,
    'travel_min_between_venues': 15,
    'result_buffer_min_between_rounds': 60,
    'semi_fraction_of_prelims': 0.5,
    'finalists_fraction_min8': 0.1,
    'checkin_buffer_min_before_first_event': 60,
    'venue_capacity_means': 'max simultaneous competitors in one heat (conservative)',
    'accessibility_mapping': 'Wheelchair->accessible=yes room (hard); Ground floor->floor 0 (hard); '
                             'Near washroom / Visual assistance -> no room data exists: kept visible, flagged for manual confirmation',
    'gender_classes': 'Female->girls blocks, Male->boys blocks, Non-binary/Prefer not to say/blank -> never auto-placed in a gendered block',
    'external_property_data': 'no accessibility or gender-segregation info exists: unverified, so hard-need people are NOT placed there',
    'budget': 'not supplied in pack: cost is shown per plan, override control required once a ceiling is set',
    'venue_features': 'venues.csv has no feature tags: mapping in VENUE_OK is an assumption, editable',
    'events_without_times': 'events.csv has no start time/venue: schedule is generated, not imported',
    'equipment_units_per_session': '1 per named item unless the text says 2 (e.g. 2 mics, 2 extension cords)',
}

# ---------------------------------------------------------------- 1. RECONCILIATION
P['a'] = pd.to_datetime(P.arrival_datetime); P['d'] = pd.to_datetime(P.departure_datetime)
P['age_i'] = P.age.astype(int)
P['minor'] = P.age_i < 18
P['gclass'] = P.gender_as_given.map({'Female': 'F', 'Male': 'M'}).fillna('U')
P['qflags'] = ''
def flag(mask, code):
    P.loc[mask, 'qflags'] = P.loc[mask, 'qflags'] + code + ';'
flag(P.d <= P.a, 'DEPARTS_BEFORE_ARRIVES')
flag(P.gender_as_given == '', 'GENDER_BLANK')
flag(P.gender_as_given == 'Prefer not to say', 'GENDER_PNTS')
flag(P.gender_as_given == 'Non-binary', 'GENDER_NONBINARY')
flag(P.dietary_needs == '', 'DIET_BLANK_UNKNOWN')
flag(P.minor, 'MINOR')
flag(P.accessibility_needs.isin(['Near washroom', 'Visual assistance']), 'NEED_UNMAPPABLE')
P['name_n'] = P.name.str.lower().str.strip()
pairs = []
for (n, c, ag), g in P.groupby(['name_n', 'college', 'age_i']):
    if len(g) < 2: continue
    rows = g.to_dict('records')
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            x, y = rows[i], rows[j]; s = 0.5
            if x['gender_as_given'] and y['gender_as_given']:
                s += 0.2 if x['gender_as_given'] == y['gender_as_given'] else -0.2
            s += 0.1 * (x['tshirt_size'] == y['tshirt_size'])
            s += 0.1 * (x['dietary_needs'] != '' and x['dietary_needs'] == y['dietary_needs'])
            s += 0.1 * (x['arrival_datetime'] == y['arrival_datetime'] and x['departure_datetime'] == y['departure_datetime'])
            if s >= 0.6:
                pairs.append(dict(id_a=x['participant_id'], id_b=y['participant_id'], name=x['name'],
                                  college=c, age=ag, score=round(s, 2),
                                  verdict='LIKELY_DUPLICATE' if s >= 0.8 else 'POSSIBLE_DUPLICATE',
                                  note='contacts differ; no auto-merge, human decision required'))
DUP = pd.DataFrame(pairs)
DUP.to_csv(f'{OUT}/duplicate_candidates.csv', index=False)
likely_secondary = set(DUP[DUP.verdict == 'LIKELY_DUPLICATE'].id_b) if len(DUP) else set()
flag(P.participant_id.isin(likely_secondary), 'LIKELY_DUP_SECONDARY')
declared = C.strength_declared.astype(int)
act = P.groupby('contingent_id').size()
CC = C.copy(); CC['declared'] = declared; CC['actual_in_file'] = CC.contingent_id.map(act)
CC['diff'] = CC.actual_in_file - CC.declared
leader_in_file = []
for _, r in C.iterrows():
    sub = P[P.contingent_id == r.contingent_id].name_n.tolist()
    leader_in_file.append((r.leader.lower() in sub, r.escort.lower() in sub))
CC['leader_in_participant_file'] = [x[0] for x in leader_in_file]
CC['escort_in_participant_file'] = [x[1] for x in leader_in_file]
CC.to_csv(f'{OUT}/contingent_reconciliation.csv', index=False)
P[P.qflags != ''][['participant_id', 'name', 'college', 'qflags']].to_csv(f'{OUT}/data_quality_flags.csv', index=False)

# ---------------------------------------------------------------- 2. ACCOMMODATION
def build_rooms():
    rooms = []
    for _, r in H.iterrows():
        rooms.append(dict(id=r.room_id, block=r.block, floor=int(r.floor), g=r.gender, cap=int(r.capacity),
                          acc=r.accessibility == 'yes', status=r.status, beds=[TS.min] * int(r.capacity), occ=[]))
    return [x for x in rooms if x['status'] == 'available']
def build_props():
    return [dict(id=r.property_id, name=r.property_name, cap=int(r.beds), rate=int(r.cost_per_bed_per_night),
                 km=float(r.distance_km), transport=r.transport_availability, beds=[TS.min] * int(r.beds),
                 conts=defaultdict(int)) for _, r in X.iterrows()]
def nights(a, d): return max(1, math.ceil((d - a).total_seconds() / 86400))
def late_night(t): return t.hour >= 22 or t.hour < 6
CLEAN = pd.Timedelta(hours=ASSUME['cleaning_hours_between_occupants'])

def allocate(mode):
    rooms, props = build_rooms(), build_props()
    out, blocks_used, floors_used, props_used = [], defaultdict(set), {}, defaultdict(set)
    Y = P[(P.accommodation_requested == 'yes') & ~P.qflags.str.contains('DEPARTS_BEFORE')].copy()
    Y['need'] = Y.accessibility_needs
    pref = C.set_index('contingent_id').preferences.to_dict()
    def free_bed(room, a): 
        for i, f in enumerate(room['beds']):
            if f <= a: return i
        return None
    def put_room(p, room, bi, why, relaxed=''):
        room['beds'][bi] = p['d'] + CLEAN; room['occ'].append((p['contingent_id'], p['a'], p['d']))
        blocks_used[p['contingent_id']].add(room['block']); floors_used.setdefault(p['contingent_id'], room['floor'])
        out.append(dict(participant_id=p['participant_id'], contingent_id=p['contingent_id'], gender_as_given=p['gender_as_given'],
                        accessibility_needs=p['accessibility_needs'], minor=p['minor'], placement='ON_CAMPUS',
                        location=room['id'], block_or_property=room['block'], from_=p['arrival_datetime'], to=p['departure_datetime'],
                        nights=nights(p['a'], p['d']), cost_inr=0, satisfied=why, relaxed=relaxed, action_needed=''))
    def eligible(p, hard):
        want = {'F': 'girls', 'M': 'boys'}.get(p['gclass'])
        if want is None: return []
        rs = [r for r in rooms if r['g'] == want]
        if p['need'] == 'Wheelchair access': rs = [r for r in rs if r['acc']]
        elif p['need'] == 'Ground floor / no stairs': rs = [r for r in rs if r['floor'] == 0]
        return rs
    def score(room, p):
        cid = p['contingent_id']; s = 0
        mine = [o for o in room['occ'] if o[0] == cid and o[1] < p['d'] and o[2] > p['a']]
        other = [o for o in room['occ'] if o[0] != cid and o[1] < p['d'] and o[2] > p['a']]
        s += 50 * bool(mine) - 40 * bool(other)
        s += 20 * (room['block'] in blocks_used[cid])
        pf = pref.get(cid, '')
        if 'ground floor' in pf: s += 15 * (room['floor'] == 0)
        if 'same floor' in pf and cid in floors_used: s += 15 * (room['floor'] == floors_used[cid])
        if 'quiet' in pf: s += 5 * (room['floor'] >= 2)
        if p['minor']: s += 3 * (room['floor'] <= 1)
        return s - 0.001 * rooms.index(room)
    def put_ext(p, why_unplaced_default=''):
        a, d = p['a'], p['d']; cid = p['contingent_id']; n = nights(a, d)
        hard = p['need'] in ('Wheelchair access', 'Ground floor / no stairs')
        if hard:
            out.append(dict(participant_id=p['participant_id'], contingent_id=cid, gender_as_given=p['gender_as_given'],
                            accessibility_needs=p['accessibility_needs'], minor=p['minor'], placement='UNPLACED', location='',
                            block_or_property='', from_=p['arrival_datetime'], to=p['departure_datetime'], nights=n, cost_inr=0,
                            satisfied='', relaxed='', action_needed='HARD NEED: no verified accessible/ground-floor bed free; verify an external property or free an accessible room (override needs reason)'))
            return
        need_tr = p['minor'] or late_night(a) or late_night(d)
        cands = [q for q in props if (q['transport'] == 'yes' or not need_tr) and any(f <= a for f in q['beds'])]
        if not cands:
            out.append(dict(participant_id=p['participant_id'], contingent_id=cid, gender_as_given=p['gender_as_given'],
                            accessibility_needs=p['accessibility_needs'], minor=p['minor'], placement='UNPLACED', location='',
                            block_or_property='', from_=p['arrival_datetime'], to=p['departure_datetime'], nights=n, cost_inr=0,
                            satisfied='', relaxed='', action_needed='SHORTAGE: no bed free in any eligible property' + (' (late-night/minor needs transport=yes)' if need_tr else '')))
            return
        low_cost = 'low cost' in pref.get(cid, '')
        if mode == 'cohesion' and not low_cost:
            key = lambda q: (-(q['id'] in props_used[cid]), q['rate'] * n, q['km'])
        else:
            key = lambda q: (q['rate'] * n, q['km'], -(q['id'] in props_used[cid]))
        q = sorted(cands, key=key)[0]
        bi = next(i for i, f in enumerate(q['beds']) if f <= a)
        q['beds'][bi] = d + CLEAN; props_used[cid].add(q['id'])
        rel = ['external_gender_segregation_unverified']
        if p['gclass'] == 'U': rel.append('gender_unconfirmed: confirm housing preference')
        if p['minor']: rel.append('MINOR_in_external: escort/guardian approval required')
        if p['need'] in ('Near washroom', 'Visual assistance'): rel.append('need_unmappable: confirm manually')
        out.append(dict(participant_id=p['participant_id'], contingent_id=cid, gender_as_given=p['gender_as_given'],
                        accessibility_needs=p['accessibility_needs'], minor=p['minor'], placement='EXTERNAL', location=q['name'],
                        block_or_property=q['id'], from_=p['arrival_datetime'], to=p['departure_datetime'], nights=n,
                        cost_inr=q['rate'] * n, satisfied='transport_ok', relaxed='|'.join(rel), action_needed=''))
    people = Y.to_dict('records')
    # pass 1: hard needs, globally by arrival (accessible beds are scarcest)
    hard1 = sorted([p for p in people if p['need'] == 'Wheelchair access'], key=lambda p: p['a'])
    hard2 = sorted([p for p in people if p['need'] == 'Ground floor / no stairs'], key=lambda p: p['a'])
    done = set()
    for p in hard1 + hard2:
        rs = [r for r in eligible(p, True) if free_bed(r, p['a']) is not None]
        if rs:
            r = max(rs, key=lambda r: score(r, p)); put_room(p, r, free_bed(r, p['a']), f"hard:{p['need']}")
        else:
            put_ext(p)
        done.add(p['participant_id'])
    # pass 2: contingents largest first; minors first, then by arrival
    order = Y.groupby('contingent_id').size().sort_values(ascending=False).index
    for cid in order:
        grp = sorted([p for p in people if p['contingent_id'] == cid and p['participant_id'] not in done],
                     key=lambda p: (not p['minor'], p['a']))
        for p in grp:
            rs = [r for r in eligible(p, False) if free_bed(r, p['a']) is not None]
            if rs:
                r = max(rs, key=lambda r: score(r, p))
                put_room(p, r, free_bed(r, p['a']), 'gender_class;capacity;window;cleaning')
            else:
                put_ext(p)
    return pd.DataFrame(out)

plans = {}
for mode in ('cohesion', 'cost'):
    df = allocate(mode); plans[mode] = df
    df.to_csv(f'{OUT}/accommodation_plan_{mode}_first.csv', index=False)
def plan_summary(df):
    g = df.groupby('contingent_id')
    s = pd.DataFrame({'requested': g.size(),
                      'on_campus': g.apply(lambda x: (x.placement == 'ON_CAMPUS').sum()),
                      'external': g.apply(lambda x: (x.placement == 'EXTERNAL').sum()),
                      'unplaced': g.apply(lambda x: (x.placement == 'UNPLACED').sum()),
                      'distinct_blocks_or_properties': g.apply(lambda x: x[x.placement != 'UNPLACED'].block_or_property.nunique()),
                      'cost_inr': g.cost_inr.sum()})
    s['split'] = s.distinct_blocks_or_properties > 1
    return s.reset_index()
for mode, df in plans.items():
    plan_summary(df).to_csv(f'{OUT}/accommodation_summary_by_contingent_{mode}_first.csv', index=False)
# peak demand by time and class
Yall = P[(P.accommodation_requested == 'yes') & ~P.qflags.str.contains('DEPARTS_BEFORE')]
peak_rows = []
for t in pd.date_range('2026-10-29 12:00', '2026-11-03 12:00', freq='6h'):
    pres = Yall[(Yall.a <= t) & (Yall.d > t)]
    peak_rows.append(dict(time=t, total=len(pres), F=(pres.gclass == 'F').sum(), M=(pres.gclass == 'M').sum(),
                          U=(pres.gclass == 'U').sum(), wheelchair=(pres.accessibility_needs == 'Wheelchair access').sum(),
                          ground_floor=(pres.accessibility_needs == 'Ground floor / no stairs').sum(),
                          girls_beds=236, boys_beds=474, external_beds=740, accessible_beds=26))
pd.DataFrame(peak_rows).to_csv(f'{OUT}/bed_demand_timeline.csv', index=False)

# ---------------------------------------------------------------- 3. SCHEDULE
VENUE_OK = {'audio; seating': ['V04', 'V02', 'V03', 'V01'], 'projector; seating': ['V02', 'V03', 'V07', 'V09'],
            'power; tables': ['V07', 'V09', 'V03', 'V08'], 'open ground': ['V04', 'V05', 'V06', 'V08'],
            'quiet room': ['V09', 'V07'], 'stage; lights': ['V01']}
HEATX = float(os.environ.get('HEATX', '1'))
VCAP = {k: int(v * HEATX) for k, v in V.set_index('venue_id').capacity.astype(int).items()}
VNAME = V.set_index('venue_id').venue_name.to_dict()
windows = []
for w in V.availability_windows.iloc[0].split(';'):
    day, rng = w.split(' '); s, e = rng.split('-'); windows.append((TS(f'{day} {s}'), TS(f'{day} {e}')))
BUF = pd.Timedelta(minutes=ASSUME['setup_teardown_min_each_side'])
TRAVEL = pd.Timedelta(minutes=ASSUME['travel_min_between_venues'])
vbusy = defaultdict(list)       # venue -> [(start,end)]
pbusy = defaultdict(list)       # participant -> [(start,end,venue)]
sessions = []
def fits(vid, s, dur, extra=None):
    e = s + dur
    if not any(ws <= s - BUF and e + BUF <= we for ws, we in windows): return False
    for bs, be in vbusy[vid]:            # stored padded: (start-BUF, end+BUF)
        if s - BUF < be and e + BUF > bs: return False
    return True
def find_slot(vid, earliest, dur, person=None, latest=None):
    cands = {earliest} | {ws + BUF for ws, _ in windows if ws + BUF >= earliest} | {be + BUF for _, be in vbusy[vid] if be + BUF >= earliest}
    for s in sorted(cands):
        if latest and s > latest: return None
        if fits(vid, s, dur):
            if person and not person_ok(person, s, dur, vid): continue
            return s
    return None
def find_slot_latest(vid, lo, hi, dur, person):
    t = hi
    while t >= lo:
        if fits(vid, t, dur) and person_ok(person, t, dur, vid): return t
        t -= pd.Timedelta(minutes=15)
    return None
def person_ok(p, s, dur, vid):
    e = s + dur
    for bs, be, bv in pbusy[p['participant_id']]:
        gap = TRAVEL if bv != vid else pd.Timedelta(0)
        if s < be + gap and e > bs - gap: return False
    return True
def present(p, s, dur): return p['a'] + pd.Timedelta(minutes=ASSUME['checkin_buffer_min_before_first_event']) <= s and s + dur <= p['d']

regs = R.merge(P[['participant_id', 'a', 'd', 'contingent_id']], on='participant_id')
regs['d_ok'] = regs.d > regs.a
E['dur'] = E.duration_minutes.astype(int); E['vopts'] = E.venue_requirements.map(VENUE_OK)
E['rounds_l'] = E.rounds.str.split('|')
ev_order = E.assign(n=E.event_id.map(regs.groupby('event_id').size()), k=E.vopts.map(len)).sort_values(['k', 'n'], ascending=[True, False]).event_id.tolist()
unscheduled_people = []
def add_session(ev, rnd, heat, vid, s, size, kind):
    sessions.append(dict(event_id=ev.event_id, event=ev.event_name, round=rnd, heat=heat, venue_id=vid, venue=VNAME[vid],
                         start=s, end=s + pd.Timedelta(minutes=ev.dur), entrants=size, entrant_basis=kind,
                         volunteers_needed=int(ev.volunteers_needed), equipment=ev.equipment_needs))
    vbusy[vid].append((s - BUF, s + pd.Timedelta(minutes=ev.dur) + BUF))
first_round = {}
WAVES = {'M': (TS('2026-10-31 08:00'), TS('2026-10-31 22:00')),
         'E': (TS('2026-10-30 08:00'), TS('2026-10-30 22:00')),
         'L': (TS('2026-11-01 08:00'), TS('2026-11-01 14:00'))}   # L = late-arrival wave (feeds finals as wildcard)
ASSUME['prelim_waves'] = 'E=30 Oct, M=31 Oct (main), L=1 Nov morning for people not on site earlier; L entrants join finals as wildcards (director decision, fairness risk)'
first_round = {}
for evid in ev_order:
    ev = E[E.event_id == evid].iloc[0]; dur = pd.Timedelta(minutes=ev.dur)
    rnds = ev.rounds_l; r1 = 'prelims' if rnds[0] == 'prelims' else 'single'
    ent = regs[(regs.event_id == evid) & regs.d_ok].sort_values('a').to_dict('records')
    heats = {w: [] for w in WAVES}
    for p in ent:
        placed = False
        for w in ('M', 'E', 'L'):
            ws, we = WAVES[w]
            for h in heats[w]:
                if len(h['m']) < VCAP[h['vid']] and present(p, h['s'], dur) and person_ok(p, h['s'], dur, h['vid']):
                    h['m'].append(p); pbusy[p['participant_id']].append((h['s'], h['s'] + dur, h['vid'])); placed = True; break
            if placed: break
            lo = max(ws, p['a'] + pd.Timedelta(minutes=ASSUME['checkin_buffer_min_before_first_event']))
            hi = min(we - dur, p['d'] - dur)
            if hi < lo: continue
            best = None
            for vid in ev.vopts:
                s_ = find_slot(vid, lo, dur, person=p, latest=hi)
                if s_ and (best is None or s_ < best[1]): best = (vid, s_)
            if best:
                h = dict(vid=best[0], s=best[1], m=[p]); heats[w].append(h)
                vbusy[best[0]].append((best[1] - BUF, best[1] + dur + BUF)); pbusy[p['participant_id']].append((best[1], best[1] + dur, best[0]))
                placed = True; break
        if not placed:
            why = 'NOT_ON_SITE_LONG_ENOUGH' if p['d'] - p['a'] < pd.Timedelta(hours=1) + dur else 'NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH'
            unscheduled_people.append(dict(participant_id=p['participant_id'], event_id=evid, reason=why, arrives=str(p['a']), departs=str(p['d'])))
    for w in WAVES:
        for i, h in enumerate(sorted(heats[w], key=lambda h: h['s'])):
            sessions.append(dict(event_id=evid, event=ev.event_name, round=r1, heat=f'{w}{i+1}', venue_id=h['vid'], venue=VNAME[h['vid']],
                                 start=h['s'], end=h['s'] + dur, entrants=len(h['m']), entrant_basis='registered (assigned)',
                                 volunteers_needed=int(ev.volunteers_needed), equipment=ev.equipment_needs))
    main_ends = [h['s'] + dur for w in ('E', 'M') for h in heats[w]]
    late_ends = [h['s'] + dur for h in heats['L']]
    first_round[evid] = (max(main_ends) if main_ends else TS('2026-10-31 09:00'), len(ent), max(late_ends) if late_ends else None)
# later rounds: placed after all first-round heats end + buffer; entrants unknown until results (assumption fractions)
unplaced_sessions = []
for rank, rname in ((1, 'semis'), (2, 'finals')):
    for evid in ev_order:
        ev = E[E.event_id == evid].iloc[0]
        if rname not in ev.rounds_l: continue
        dur = pd.Timedelta(minutes=ev.dur)
        prev = [s for s in sessions if s['event_id'] == evid]
        base = [s['end'] for s in prev if not (str(s['heat']).startswith('L') and rname == 'semis')]
        earliest = (max(base) if base else first_round[evid][0]) + pd.Timedelta(minutes=ASSUME['result_buffer_min_between_rounds'])
        n1 = first_round[evid][1]
        n = math.ceil(n1 * ASSUME['semi_fraction_of_prelims']) if rname == 'semis' else max(8, math.ceil(n1 * ASSUME['finalists_fraction_min8']))
        remaining, hn = n, 1
        while remaining > 0:
            best = None
            for vid in ev.vopts:
                s = find_slot(vid, earliest, dur)
                if s and (best is None or s < best[1]): best = (vid, s)
            size = min(remaining, VCAP[best[0]]) if best else remaining
            if best is None:
                unplaced_sessions.append(dict(event_id=evid, event=ev.event_name, round=rname, entrants=remaining,
                                              reason='no venue window left before fest end'))
                break
            add_session(ev, rname, hn, best[0], best[1], size, 'ASSUMED qualifiers (unknown until results)')
            remaining -= size; hn += 1
SES = pd.DataFrame(sessions).sort_values(['start', 'venue_id'])
SES.to_csv(f'{OUT}/schedule_plan.csv', index=False)
pd.DataFrame(unscheduled_people).to_csv(f'{OUT}/schedule_unscheduled_entrants.csv', index=False)
pd.DataFrame(unplaced_sessions).to_csv(f'{OUT}/schedule_unplaced_sessions.csv', index=False)
# independent conflict check
conf = []
for vid, g in SES.groupby('venue_id'):
    g = g.sort_values('start').to_dict('records')
    for x, y in zip(g, g[1:]):
        if y['start'] - BUF < x['end'] + BUF: conf.append(dict(kind='VENUE_OVERLAP', a=f"{x['event_id']} {x['round']}", b=f"{y['event_id']} {y['round']}", venue=vid))
# staff / volunteers vs on-shift core team; equipment vs good stock
def shift_count(t):
    n = 0
    for sh in T['shift']:
        a, b = sh.split('-'); ha, hb = int(a[:2]), int(b[:2]); h = t.hour
        n += (ha <= h < hb) if ha < hb else (h >= ha or h < hb)
    return n
EQ = {'barricades': ('barricade', 1), 'tables': ('table', 1), 'projector': ('projector', 1), 'camera': ('camera', 1),
      'tripod': ('tripod', 1), '2 extension cords': ('extension cord', 2), '2 mics': ('mic', 2), '1 speaker': ('speaker', 1)}
good = L.assign(q=L.quantity.astype(int)).groupby(['item', 'condition']).q.sum().unstack(fill_value=0)
rows = []
for t in pd.date_range('2026-10-30 08:00', '2026-11-01 20:00', freq='30min'):
    act = SES[(SES.start <= t) & (SES.end > t)]
    if act.empty: continue
    vol = int(act.volunteers_needed.sum()); on = shift_count(t)
    row = dict(time=t, sessions=len(act), volunteers_needed=vol, core_team_on_shift=on, volunteer_gap=max(0, vol - on))
    need = defaultdict(int)
    for _, s in act.iterrows():
        for part in s.equipment.split(';'):
            part = part.strip()
            if part in EQ: need[EQ[part][0]] += EQ[part][1]
    for it, q in need.items():
        row[f'need_{it}'] = q
        gd = int(good.loc[it, 'good']) if it in good.index and 'good' in good.columns else 0
        row[f'good_{it}'] = gd; 
    rows.append(row)
LOAD = pd.DataFrame(rows).fillna(0); LOAD.to_csv(f'{OUT}/resource_load_timeline.csv', index=False)
eq_gap = []
for it in good.index:
    nc = f'need_{it}'
    if nc in LOAD:
        pk = LOAD[nc].max(); gd = int(good.loc[it].get('good', 0)); chk = int(good.loc[it].get('needs check', 0)); rep = int(good.loc[it].get('under repair', 0))
        eq_gap.append(dict(item=it, peak_concurrent_need=int(pk), good=gd, needs_check=chk, under_repair=rep,
                           status='SHORT even with needs-check units' if pk > gd + chk else ('AT RISK (relies on needs-check units)' if pk > gd else 'OK')))
pd.DataFrame(eq_gap).to_csv(f'{OUT}/equipment_gap.csv', index=False)
pd.DataFrame(conf).to_csv(f'{OUT}/schedule_conflict_check.csv', index=False)

# ---------------------------------------------------------------- 4. MERCH + VENDORS
Mm = M.copy(); Mm['qty'] = Mm.quantity.astype(int); Mm['reserved'] = Mm.reserved_quantity.astype(int); Mm['issuable'] = Mm.qty - Mm.reserved
ts = P.tshirt_size.value_counts()
nP = len(P); dedupe_n = len(P) - len(likely_secondary)
Mm['demand_raw'] = [ts.get(s, 0) if i == 'T-shirt' else nP for i, s in zip(Mm.item, Mm['size'])]
Mm['shortfall'] = (Mm.demand_raw - Mm.issuable).clip(lower=0)
Mm['note'] = ['demand = one per participant-record' if i != 'winner medal' else 'demand depends on winners: not a per-head item'
              for i in Mm['item']]
Mm.loc[Mm['item'] == 'winner medal', ['demand_raw', 'shortfall']] = [0, 0]
Mm.drop(columns=['quantity', 'reserved_quantity']).to_csv(f'{OUT}/merch_plan.csv', index=False)
VN2 = VN.copy(); VN2['cert'] = pd.to_datetime(VN2.hygiene_certificate_expiry)
def cert_status(d):
    if d < TS('2026-10-30'): return 'EXPIRED before fest'
    if d < TS('2026-11-01'): return 'EXPIRES DURING FEST'
    return 'valid through fest'
VN2['cert_status'] = VN2.cert.map(cert_status); VN2['cap'] = VN2.capacity.astype(int)
VN2['label_flag'] = ''
VN2.loc[VN2.menu.str.contains('Vegan') & ~VN2.dietary_options.str.contains('vegan'), 'label_flag'] = 'menu says vegan but dietary_options does not list vegan (and lists non-vegetarian)'
VN2.loc[VN2.menu.str.contains('Jain') & ~VN2.dietary_options.str.contains('jain'), 'label_flag'] = 'menu says Jain thali but dietary_options has no jain tag: confirm with vendor'
VN2.drop(columns=['cert']).to_csv(f'{OUT}/vendor_compliance.csv', index=False)
diet_map = {'Vegetarian': 'vegetarian', 'Non-vegetarian': 'non-vegetarian', 'Halal': 'halal', 'Jain': 'jain', 'Gluten-free': 'gluten-free', 'Nut allergy': 'nut-free'}
cov = []
for dn, tag in diet_map.items():
    ok = VN2[VN2.dietary_options.str.contains(tag) & (VN2.cert_status == 'valid through fest')]
    anyv = VN2[VN2.dietary_options.str.contains(tag)]
    cov.append(dict(diet=dn, people_in_file=int((P.dietary_needs == dn).sum()), vendors_declaring=len(anyv),
                    vendors_with_valid_cert_all_fest=len(ok), valid_vendor_capacity=int(ok.cap.sum()),
                    status='GAP: no compliant vendor' if len(ok) == 0 else 'ok'))
cov.append(dict(diet='(blank = UNKNOWN)', people_in_file=int((P.dietary_needs == '').sum()), vendors_declaring='', vendors_with_valid_cert_all_fest='',
                valid_vendor_capacity='', status='UNKNOWN: not treated as no restriction; confirm at check-in'))
pd.DataFrame(cov).to_csv(f'{OUT}/vendor_diet_coverage.csv', index=False)
pd.DataFrame([dict(k=k, v=v) for k, v in ASSUME.items()]).to_csv(f'{OUT}/assumptions.csv', index=False)

# ---------------------------------------------------------------- SUMMARY
def pstat(df):
    return dict(requested=len(df), on_campus=int((df.placement == 'ON_CAMPUS').sum()), external=int((df.placement == 'EXTERNAL').sum()),
                unplaced=int((df.placement == 'UNPLACED').sum()),
                unplaced_hard_need=int(((df.placement == 'UNPLACED') & df.action_needed.str.startswith('HARD')).sum()),
                unplaced_gender_unconfirmed=int(((df.placement == 'UNPLACED') & (df.gender_as_given.isin(['', 'Prefer not to say', 'Non-binary']))).sum()),
                minors_in_external=int(((df.placement == 'EXTERNAL') & df.minor).sum()), cost_inr=int(df.cost_inr.sum()),
                contingents_split=int(plan_summary(df).split.sum()))
summary = dict(
    raw_records=nP, declared_strength_total=int(declared.sum()), narrative=2400, invalid_interval=int(P.qflags.str.contains('DEPARTS_BEFORE').sum()),
    likely_dup_pairs=int((DUP.verdict == 'LIKELY_DUPLICATE').sum()) if len(DUP) else 0, possible_dup_pairs=int((DUP.verdict == 'POSSIBLE_DUPLICATE').sum()) if len(DUP) else 0,
    leaders_in_file=int(CC.leader_in_participant_file.sum()), escorts_in_file=int(CC.escort_in_participant_file.sum()),
    accommodation_yes=int((P.accommodation_requested == 'yes').sum()),
    plan_cohesion=pstat(plans['cohesion']), plan_cost=pstat(plans['cost']),
    sessions=len(SES), unscheduled_entrants=len(unscheduled_people), unplaced_sessions=len(unplaced_sessions), venue_overlaps=len(conf),
    peak_volunteer_gap=int(LOAD.volunteer_gap.max()), hours_with_volunteer_gap=int((LOAD.volunteer_gap > 0).sum() / 2),
    team_events_missing_team_id=int(((regs.event_id.isin(E[E.type == 'team'].event_id)) & (regs.team_id == '')).sum()))
summary['heat_capacity_factor'] = HEATX
json.dump(summary, open(f'{OUT}/summary.json', 'w'), indent=2, default=str)
print(json.dumps(summary, indent=2, default=str))
