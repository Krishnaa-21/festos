# FestOS Master 7-Minute Live Demo Script

> **Event:** Aarohan Festival (EPINOIA 2026, IIM Indore)  
> **Target Duration:** Exactly 7 Minutes (0:00 – 7:00) + 3 Minutes Q&A  
> **Presenters:**
> - **Speaker 1 (Product & Operations Lead):** The Festival Problem, Data Reconciliation Gap, Live Hostel Disruption & Synthesis.
> - **Speaker 2 (Optimization & Decisions Lead):** Accommodation Plans A/B/C, Why-not? Diagnosis, Scheduling & Vendors.
> - **Speaker 3 (Architecture & Security Lead):** RBAC, Break-Glass Audit Trail, Offline PWA Scanning, Assumptions & AI Disclosure.

---

## Timeline & Presentation Run-Sheet

```text
+----------------------------------------------------------------------------------------------------+
| 0:00   0:45           1:45          3:00             4:30             5:30        6:15   6:45  7:00|
|  [Problem] [Reconciliation] [Accom Plans]  [Hostel Disruption] [Sched & Vendors] [Security] [Lim] [AI]|
|   Spk 1        Spk 1           Spk 2             Spk 1             Spk 2           Spk 3    Spk 3 Spk3 |
+----------------------------------------------------------------------------------------------------+
```

---

### ACT 1: The Festival Operational Problem (0:00 – 0:45)
**Speaker:** Speaker 1 (Operations Lead)  
**Starting Screen:** `http://localhost:5173/dashboard` (Executive Overview)

- **Spoken Narrative:**
  > *"Judges, imagine running Aarohan 2026: 38 university contingents, 31 simultaneous competitive events, 14 vendors, and 1,450 beds spread across campus and off-campus resorts. In every previous edition, the festival was managed through disjointed WhatsApp groups and spreadsheet silos. When a hostel floods or a contingent bus gets delayed on the highway, spreadsheets don’t recalculate the blast radius. Organizers find out after participants are stranded.*
  >
  > *FestOS is not a registration portal. It is the real-time operational command center for festival organizers. Every decision has an explainable reason; every change updates downstream subsystems; and our core principle is: **AI proposes. Deterministic logic validates. Humans approve.**"*

- **Exact Actions & On-Screen Results:**
  1. Point to **Command Overview KPI Bar**:
     - *Shows:* **2,836 Raw** vs **2,842 Declared** vs **2,400 Narrative Claim**.
     - *Shows:* **1,450 Beds (710 Campus / 740 External)**.
  2. Highlight the **Prioritised Attention Queue** (`data-testid="attention-queue-section"`):
     - Point out top attention item: *Accessibility Arrival Imminent (3 Wheelchair participants)*.
     - Note the mathematical Attention Score: $\text{Severity } (4) \times \text{Urgency } (5) \times \text{People } (3) = 60$.

---

### ACT 2: Data Reconciliation & Actual Operational Gaps (0:45 – 1:45)
**Speaker:** Speaker 1 (Operations Lead)  
**Navigation:** Click **Reconciliation** on sidebar (or press keyboard chord `G` then `R`). URL: `/reconciliation`

- **Spoken Narrative:**
  > *"Rule number one of FestOS: **Never force 2,400.** The festival prospectus claimed approximately 2,400 participants. But when we import the raw university registration CSVs, there are exactly 2,836 individual records, while the 38 college contingent declarations claim 2,842.*
  >
  > *Watch our Reconciliation Waterfall: 2,400 portal records are deduped; 436 late arrivals are captured; and we uncover an **Unexplained Remainder of 426 participants** that spreadsheets silently dropped. FestOS preserves every raw record, flags 3 malformed rows in quarantine, and highlights 12 candidate duplicate registrations for human review without auto-merging."*

- **Exact Actions & On-Screen Results:**
  1. Click **Data Reconciliation Waterfall** tab:
     - *On Screen:* Step graph showing `2,836 Raw` $\rightarrow$ `2,833 Validated` $\rightarrow$ `3 Quarantined` $\rightarrow$ `426 Unexplained Gap`.
  2. Click **Duplicates Workbench** tab:
     - Select duplicate candidate pair `P0102` (Aarav Sharma, IIT Bombay) and `P0103` (Aarav Sharma, IITB duplicate).
     - Click **Compare Side-by-Side**: Shows matching email and phone, but differing dates of birth.
     - Note the button: **Keep Separate** vs **Merge with Reason**.

---

### ACT 3: Accommodation Allocation Plans A/B/C & Explainability (1:45 – 3:00)
**Speaker:** Speaker 2 (Optimization Lead)  
**Navigation:** Click **Accommodation** on sidebar (`/accommodation`).

- **Spoken Narrative:**
  > *"Accommodation is where festival budgets live or die. We implemented three distinct deterministic allocation strategies rather than a black-box optimizer.*
  >
  > * **Plan A (Cohesion-First):** Keeps university teams in contiguous corridors. Costs ₹42,500 extra in external hotels because campus rooms fill fast, but contingent morale is 100%.
  > * **Plan B (Cost-First):** Minimizes budget to ₹21,000 extra by splitting students into scattered remnant beds. Cohesion drops by 38%.
  > * **Plan C (Balanced Optimization):** The weighted equilibrium (50% cohesion, 30% cost, 20% travel proximity).
  >
  > *Now look at this: what happens when a student cannot be placed? In legacy tools, you get an empty cell. In FestOS, click **Why-not?**"*

- **Exact Actions & On-Screen Results:**
  1. Toggle between **Plan A**, **Plan B**, and **Plan C** cards:
     - *On Screen:* Metrics update instantly: Cost delta, Cohesion score, Average travel time.
  2. Point to the **Bed Occupancy Timeline Scrubber** (Day 1 Peak: 1,440 beds).
  3. Click **Why-not? Diagnosis Drawer** on unplaced participant `P0281`:
     - *On Screen Drawer opens:* Identifies exact constraint bottlenecks:
       - $\checkmark$ Gender compatibility: Male hostel verified.
       - $\times$ **Cleaning Turnaround Buffer:** 180-minute buffer active until 14:00.
       - $\times$ **Ground Floor Accessibility:** Participant requires wheelchair access; zero ground floor beds left on campus.
     - Explains why external booking at Lakeview Resort is mandatory.

---

### ACT 4: Live Disruption Injection & Blast Radius Analysis (3:00 – 4:30)
**Speaker:** Speaker 1 (Operations Lead)  
**Navigation:** Click **Incident Center** on sidebar (`/incidents`).

- **Spoken Narrative:**
  > *"Now for the core test: a real disruption during festival operations. It’s 06:30 AM on Day 2. A primary plumbing main line bursts in Hostel 3 basement, flooding electrical shafts. 85 students are displaced immediately.*
  >
  > *Watch how fast an authorized organizer handles this in under 30 seconds using the keyboard alone."*

- **Exact Actions & On-Screen Results:**
  1. Click **Inject Disruption** on the **Hostel Closure Card** (`data-testid="launch-btn-hostel_closure"`):
     - *Modal opens:* Parameter form pre-filled with Hostel 3 (85 affected beds).
  2. Click **Preview Impact (Dry Run)** (`data-testid="preview-impact-btn"`):
     - *On Screen:* Dry-run calculates the blast radius in 76ms:
       - 85 participants unplaced.
       - 2 event heats delayed.
       - 7 shuttle loops required.
       - Annapurna West mess redirected.
  3. Click **Compare Recovery Plans** (`data-testid="compare-plans-btn"`):
     - Shows Plan A (Reallocate to Lakeview Resort, +₹42,500) vs Plan B (Disperse across town).
  4. Click **Authorize & Commit Plan** (`data-testid="approve-plan-btn"`):
     - *On Screen:* `ConfirmWithReason` modal appears.
     - Demonstrate: **Confirm button is completely disabled** when reason is blank.
     - Type rationale: `"Hostel 3 plumbing flooded electrical conduits; evacuating 85 students to Lakeview Resort under Plan A."`
     - Click **Confirm**: Execution bar runs transactional unit through ChangeService.
  5. *On Screen:* **Verification Screen** appears:
     - Before vs After delta: Unplaced participants drop from 85 to 0.
     - Downstream Update Tracker:
       - Accommodation: `UPDATED` (Lakeview Resort rooms blocked).
       - Transport: `UPDATED` (7 shuttle runs scheduled).
       - Catering: `UPDATED` (85 meal tokens redirected).
  6. Click **Inspect Impact Tree** button:
     - URL navigates to `/impact`.
     - *On Screen:* Interactive Visual Impact Tree expands showing root incident $\rightarrow$ Accommodation $\rightarrow$ Transport $\rightarrow$ 85 individual participant nodes.

---

### ACT 5: Scheduling, Inventory & Vendor Operations (4:30 – 5:30)
**Speaker:** Speaker 2 (Optimization Lead)  
**Navigation:** Navigate to `/events` and `/merchandise`.

- **Spoken Narrative:**
  > *"Next: Operations under pressure. Zero venue overlaps does not mean zero schedule conflicts. FestOS evaluates all 10 conflict types: participant overlaps, judge travel windows, volunteer shift fatigue, equipment shortages, and sound bleed.*
  >
  > *Now look at the Merchandise counter. A classic festival fraud is double-claiming delegate kits across different desks. In FestOS, our SQLite engine enforces a hard atomic database constraint: `UNIQUE(canonical_participant_id, item_id)`."*

- **Exact Actions & On-Screen Results:**
  1. In `/events`: Click **Conflict Panel**:
     - *On Screen:* Highlights Camera Shortage for RoboWars (3 cameras demanded vs 2 available). Shows automated recommendation: *Relocate Drone Camera 01 from Auditorium Stage during break*.
  2. In `/merchandise`:
     - Scan QR for participant `P0102` $\rightarrow$ T-Shirt issued cleanly.
     - Immediately re-scan QR for `P0102` at Counter 2.
     - *On Screen:* Giant Red Alert: **ALREADY ISSUED (409 Conflict)**.
     - Displays original transaction metadata: *Claimed at 08:35 AM at North Counter by Volunteer Pooja Sharma*.

---

### ACT 6: Security, RBAC & Immutable Audit Trail (5:30 – 6:15)
**Speaker:** Speaker 3 (Tech & Security Lead)  
**Navigation:** Navigate to `/audit` and open Mobile View.

- **Spoken Narrative:**
  > *"FestOS is built on zero-trust role-based access control. Volunteers on the ground have no access to director budgets or participants' personal phone numbers and medical conditions.*
  >
  > *If an emergency arises—say, a participant collapses from an allergic reaction—we provide a **Break-Glass Emergency Protocol**. Watch this: an organizer clicks Break-Glass, provides a mandatory medical rationale, and the unmasked contact is revealed for exactly 15 minutes. Crucially, that break-glass action creates an indelible, append-only audit event in our cryptographic SHA-256 ledger."*

- **Exact Actions & On-Screen Results:**
  1. In `/participants`:
     - Point to Masked Fields: Phone `+91 ••••• •••10` with red **BREAK GLASS** badge.
     - Click **BREAK GLASS**: Dialog requires operational reason. Type `"Severe anaphylactic allergic reaction; emergency physician contact required."`
     - Click Confirm: Real phone unmasked; notification toast logged.
  2. In `/audit`:
     - *On Screen:* Latest audit entry shows: `security.break_glass_unmask` by `Devashish Roy` with timestamp, reason, and previous cryptographic hash.
  3. Show **Volunteer Mobile View** (toggle 360px viewport or switch to Volunteer role):
     - *On Screen:* Restricted to 2 giant touch buttons: Check-in & Merchandise. High-contrast, audio feedback beeps, no sensitive tabs.

---

### ACT 7: Assumptions, Limitations & AI Disclosure (6:15 – 7:00)
**Speaker:** Speaker 3 (Tech & Security Lead)  
**Navigation:** Navigate to `/reports` $\rightarrow$ Click **Assumptions & Limitations** tab.

- **Spoken Narrative:**
  > *"Finally, we believe in honest engineering. We never pretend heuristic software is omniscient.*
  >
  > * *Assumptions are explicit:* Our cleaning buffer is explicitly parameterized at 180 minutes. The festival prospectus narrative count of 2,400 is documented as an assumption, never forced on raw data.
  > * *AI Disclosure:* AI assisted in code scaffolding, test case generation, and natural-language regex command parsing. But **deterministic code validates all constraints**, and **human organizers authorize all changes**.
  >
  > *In 7 minutes, we showed you real data reconciliation, three transparent housing plans, a live 85-bed hostel evacuation with downstream cascading updates, duplicate merchandise prevention, break-glass security, and instant rollback. FestOS is ready for Aarohan 2026."*

- **Exact Actions & On-Screen Results:**
  1. Show **Assumptions Register Table**:
     - Highlights: `cleaning_buffer_minutes = 180`, `shuttle_capacity_seats = 12`, `minor_age_threshold = 18`.
  2. Click **Download Bundle (.ZIP)** (`data-testid="bundle-zip-btn"`):
     - Shows all 20 Section 14 auditable CSV/MD exports.
  3. Conclude on time: **6:58 elapsed!**

---

## Post-Demo Reset (For Subsequent Rehearsal Run)
Run in terminal:
```bash
make reset-demo
```
*Execution takes 0.08 seconds.* System is back to pristine initial state for Run 2!

