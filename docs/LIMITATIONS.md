# FestOS Known System & Operational Limitations (`docs/LIMITATIONS.md`)

> **Festival:** Aarohan (EPINOIA 2026, IIM Indore)  
> **Philosophy:** Honesty over hype. We explicitly disclose boundaries, assumptions, heuristic compromises, and data realities to ensure safe, defensible operational decisions.

---

## 1. Executive Summary of Key Limitations

| Domain | Limitation | Operational Reality | FestOS Mitigation / Defense |
|---|---|---|---|
| **Accommodation** | Greedy heuristic allocation | Heuristics do not guarantee global mathematical optimality (NP-hard). | Computes 3 transparent heuristic plans (A: Cohesion, B: Cost, C: Balanced) in <100ms; provides explicit **Why-not?** diagnostic trees. |
| **Transport** | Assumed shuttle & travel values | Data pack contains no transit telemetry or shuttle fleet schedules. | Parameterized travel matrices (15 min campus, 25 min external); shuttle routes marked `ASSUMED` with visible capacity alerts. |
| **Integrations** | No real SMS / WhatsApp / Bus API | Broadcast channels and vehicle GPS are simulated / mocked. | Fully functional draft generation across 5 audiences; mock dispatcher requires human approval before logging delivery. |
| **Data Verification** | Unverified vendor & accessibility info | External properties lack gender-segregation and accessibility audit data. | Gateway-level safety blocks: participants with hard accessibility needs are blocked from unverified external stays until confirmed. |
| **Data Fidelity** | Synthetic benchmark data | Participant rosters, event times, and phone numbers are synthetically generated. | Realistic edge cases embedded (malformed datetimes, duplicate names, minors); full tolerant parser and quarantine pipeline. |
| **Architecture** | SQLite concurrency constraints | SQLite uses file-level write locking; not designed for high-throughput distributed writes. | WAL mode enabled (`PRAGMA journal_mode=WAL`), optimistic concurrency via `expected_version`, and atomic single-transaction `ChangeService`. |
| **Scheduling** | Missing schedule primitives in pack | `events.csv` lacks session start times, venues, judge profiles, and team IDs. | Baseline schedule marked `ASSUMED`; 10 conflict checkers identify volunteer fatigue, equipment clashes, and room turnaround deficits. |
| **Headcount** | Reconciliation variance | 2,836 raw vs 2,400 narrative vs 2,842 declared strength. | Golden Headcount Waterfall surfaces the 426 unexplained remainder for committee review rather than forcing 2,400. |

---

## 2. Detailed Technical & Operational Disclosures

### 2.1 Heuristic Allocation vs. Optimal Solvers
- **The Tradeoff:** Exact Mixed-Integer Linear Programming (MILP) solvers (such as OR-Tools or Gurobi) on 2,836 participants and 1,450 beds across multiple festival days take minutes to solve and behave as black boxes. When constraints are slightly over-constrained, MILP solvers return `INFEASIBLE` without actionable recourse.
- **The Heuristic Choice:** FestOS employs deterministic, greedy allocation heuristics with multi-pass constraint validation.
- **Limitation:** The generated plans (Plan A, Plan B, Plan C) are heuristically optimized according to clear priority order, but are **not provably optimal**. For instance, Plan A accepts higher lodging costs (+₹42,500) to keep university contingents in contiguous hostel blocks, while Plan B fragments contingents to maximize free campus beds (+₹21,000).

### 2.2 Assumed Travel Times & Simulated Shuttle Operations
- **Data Gap:** The raw data pack provides no fleet telemetry, route geometry, or traffic congestion data for Indore transit.
- **Assumed Baselines:**
  - Campus intra-venue walking time: `15 minutes` (`venue_travel_min = 15`).
  - Campus-to-external property transit time: `25 minutes` (`shuttle_travel_min = 25`).
  - Fleet sizing: `3 shuttle vans` with `12 seats each` (`shuttle_vehicle_count = 3`, `shuttle_capacity_seats = 12`).
  - Operating window: `06:00 to 22:00`.
- **Limitation:** Real traffic surges, bypass delays, or rain-induced transit delays cannot be predicted from static CSVs. Organizers must use the **Incident Center** to inject live transport delays (e.g. `BUS_DELAY`, `LATE_CONTINGENT`).

### 2.3 Simulated External Integrations
- **Notifications:** FestOS generates communication drafts across 5 stakeholder audiences (`contingent_leaders`, `volunteers`, `vendors`, `accommodation_coordinators`, `event_organisers`). However, real telecommunication SMS gateways (Twilio / Gupshup) and WhatsApp Business APIs are not bound. The system dispatches mock notifications to an internal delivery log (`NotificationDeliveryLog`) and strictly enforces prior human approval.
- **Payment & Banking:** Vendor settlement and emergency disbursements are recorded via audited double-entry accounting records (`finance.record_payment`), but do not execute live NEFT/RTGS bank wire transfers.

### 2.4 Unverified External Property Data & Safety Boundaries
- **Accessibility Deficit:** In `participants.csv`, 256 participants request accessibility assistance (128 visual assistance, 128 proximity to washroom). However, `hostels.csv` only records wheelchair ramp access (`accessible: yes/no/limited`).
- **External Property Suitability:** External hotels (`external_stays.csv`) have unverified floor plans, gender segregation policies, and accessibility capabilities (`external_property_accessibility = UNVERIFIED`).
- **Enforced Safety Barrier:** FestOS prohibits the automated assignment of participants with hard accessibility needs to external properties. They are flagged on the **Unknowns Burn-Down Queue** for manual coordinator inspection.

### 2.5 Synthetic Data Pack Imperfections
- All 2,836 participant records, phone numbers (+91-8480...), and contingent rosters are synthetically synthesized for competition benchmarking.
- **Embedded Imperfections:**
  - Exactly 3 records have arrival datetimes after departure datetimes (`P0037`, `P1189`, `P2034`).
  - 279 participants are age 17 (minors requiring guardian consent).
  - 1,262 participants have non-binary, prefer not to say, or missing gender, yet campus hostels offer 0 gender-neutral rooms.
  - 14 food vendors show critical dietary coverage gaps in Jain, Gluten-Free, and Nut-Free offerings.

### 2.6 SQLite Database Concurrency & Scale
- **Storage Engine:** FestOS defaults to SQLite running with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and `PRAGMA synchronous=NORMAL`.
- **Concurrency Boundary:** SQLite supports unlimited concurrent readers, but serializes writes through a single database lock. While entirely sufficient for fest operations (~50 concurrent desk volunteers and coordinators), it cannot scale to tens of thousands of writes per second without migrating to PostgreSQL.
- **Defense Implemented:** Optimistic concurrency control via `expected_version` in mutating API request payloads returns `409 VERSION_CONFLICT` if state changes between read and write.

### 2.7 Schedule Quality Bound by Missing Primitives
- **Data Gap:** `events.csv` only contains event name, duration, and participant limits. It contains **no scheduled times, no allocated venues, no judge profiles, and no team IDs**.
- **Missing Team IDs:** Exactly 1,810 registrations belong to 10 team events (`solo_team == 'team'`), and 100% of these 1,810 rows lack a `team_id`.
- **Limitation:** Any schedule produced by FestOS is an **assumed provisional schedule**. All generated sessions are flagged `ASSUMED`. Judge assignments appear as open staffing vacancies requiring committee nomination.

### 2.8 The Golden Headcount Reconciliation Outcome
- **The Discrepancy:**
  - **Raw Roster Records:** 2,836 rows in `data/raw/participants.csv`.
  - **Contingent Declared Total:** 2,842 participants declared in contingent headers (`contingents.csv`).
  - **Narrative Planning Target:** 2,400 participants mentioned in the original marketing prospectus.
  - **The Net Gap:** An unexplained remainder of **426 participants** (or 436 over narrative).
- **The Decision:** FestOS **never forces 2,400**. Silently dropping 426-436 real students would cause catastrophic arrival chaos. FestOS maintains the **Golden Headcount Waterfall** in the Data Reconciliation dashboard, transparently surfacing the gap for festival leadership sign-off.
