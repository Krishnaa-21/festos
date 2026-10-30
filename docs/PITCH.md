# FestOS Pitch Deck Outline & 3-Minute Q&A Defense Guide

> **Festival:** Aarohan (EPINOIA 2026, IIM Indore)  
> **Presentation Window:** 7-Minute Pitch + 3-Minute Q&A  
> **Core Proposition:** FestOS is an explainable, disruption-resilient operational command center where **AI proposes, deterministic logic validates, and humans approve**.

---

## Part 1: Slide Outline (Clear Choices, Evidence & Limitations)

### Slide 1: Title & The Operational Reality
- **Headline:** FestOS — The Command Center for Festival Resilience
- **The Core Problem:** Managing 2,836 participants, 38 contingents, 31 events, and 1,450 beds across town cannot be done on spreadsheets and WhatsApp.
- **The Central Thesis:** In a live festival, a single disruption cascades across accommodation, transport, food, and stages. Software must compute the blast radius before humans make a move.
- **Key Visual:** Overview command dashboard with real-time Attention Queue and Risk Heatmap.

### Slide 2: Data Reconciliation (Why We Never Force 2,400)
- **Clear Choice:** We refused to artificially force the 2,400 prospectus number.
- **Evidence:**
  - Raw records imported: **2,836**.
  - Contingent declarations: **2,842**.
  - Narrative claim: **2,400**.
  - **Unexplained Remainder of 426 participants** surfaced and flagged for audit, rather than silently truncated.
- **Data Quality:** 3 quarantined malformed records, 12 duplicate candidates flagged for human review without dangerous auto-merges.

### Slide 3: Three Transparent Accommodation Plans (A, B, and C)
- **Clear Choice:** Reject black-box solvers in favor of three defensible, deterministic heuristics:
  - **Plan A (Cohesion-First):** Preserves university contingent blocks; accepts external resort travel; +₹42,500 cost.
  - **Plan B (Cost-First):** Minimizes off-campus spending (+₹21,000); scatters teams across remaining beds.
  - **Plan C (Balanced Optimization):** 50% cohesion, 30% cost, 20% travel proximity.
- **Explainability Innovation:** The **Why-not?** diagnostic panel explaining exact constraint blockages (e.g. cleaning buffer or wheelchair accessibility deficit).

### Slide 4: Real Disruption Management & The Change Impact Engine
- **Clear Choice:** Built a unified Disruption Console covering all seven mandatory live-test scenarios.
- **Live Proof:** Hostel 3 plumbing failure displaces 85 beds:
  - Dry-run impact computed in 76ms.
  - Multi-plan comparison side-by-side.
  - Mandatory operational justification recorded via `ConfirmWithReason`.
  - Transactional commit through `ChangeService`.
  - Cascading downstream tracker: Accommodation reallocated, 7 shuttle loops dispatched, Annapurna West catering tokens redirected.

### Slide 5: Scheduling, Inventory & Vendor Reliability
- **Scheduling Rigor:** Evaluates all 10 conflict types beyond venue overlap (volunteer fatigue, camera shortages, judge transit).
- **Physical Inventory Ledger:** Stock balance equations prevent double-crediting in-transit or damaged equipment.
- **Merchandise Fraud Prevention:** Hard database guarantee `UNIQUE(canonical_participant_id, item_id)` rejects repeat QR scans with `409 ALREADY_ISSUED` and surfaces original handover details.
- **Vendor Dietary Shield:** Tracks meal slot and dietary compatibility (Jain, Vegan, Gluten-Free) rather than aggregate headcounts.

### Slide 6: Security, RBAC & Offline Tolerance
- **Zero-Trust Access:** 9 operational roles with strict permission scopes.
- **Volunteer Terminal Isolation:** Mobile view restricted to Check-in and Merchandise counter flows with giant touch targets, audio beeps, and zero personal data exposure.
- **Break-Glass Elevation:** Emergency unmasking requires justification and writes an immutable cryptographic audit record.
- **PWA Offline Resilience:** Wi-Fi drops buffer scans in IndexedDB (Dexie); on reconnect, batch sync enforces exactly-once application and ignores duplicates.

### Slide 7: Honest Engineering, Assumptions & AI Disclosure
- **Assumptions Register:** 180-minute cleaning buffer, 12-seat shuttle capacity, and 18-year minor threshold are parameterized and visible.
- **AI Boundary:** AI suggests plans, analyzes text commands, and drafts communications. **Deterministic rules validate hard constraints. Humans approve.**
- **Instant Rehearsal:** `make reset-demo` restores known pristine state in **0.08 seconds**.

---

## Part 2: 3-Minute Q&A Defense Guide (The Tough Judge Questions)

### Q1: "The problem narrative states ~2,400 participants, but your database has 2,836. Why didn't your system normalize to 2,400?"
> **Answer:**  
> *"Because in real operations, truncation is catastrophic. The 2,400 figure was an initial marketing prospectus estimate. When the registration portal closed, there were 2,836 individual submitted rows, and the 38 college contingent leaders officially declared 2,842 participants.  
> If our software had silently forced 2,400, exactly 436 real students would have arrived at the campus gates with valid college ID cards and found no room, no meal token, and no event slot. FestOS made the architectural choice to show the Golden Headcount Waterfall: 2,400 verified portal entrants, 436 late arrivals, and an explicit **Unexplained Remainder of 426** that requires committee sign-off. We solve real operational gaps rather than massaging numbers to look tidy."*

---

### Q2: "Why did you use heuristic allocation algorithms instead of an optimal integer linear programming (MILP) solver like OR-Tools or Gurobi?"
> **Answer:**  
> *"We benchmarked both. An exact MILP solver on 2,836 participants and 1,450 beds across 72 hours takes minutes to compute and behaves like an unexplainable black box under pressure. If a single constraint is slightly unsatisfiable, MILP returns an unhelpful `INFEASIBLE`.  
> In festival operations, organizers need solutions in under one second, and they need to know **why** a decision was made. Our heuristic solver runs in under 100 milliseconds, produces three defensible plans (Cohesion, Cost, Balanced), and provides an explicit **Why-not?** diagnostic tree for any unplaced participant. When Hostel 3 flooded at 6:30 AM, our heuristic relocated 85 students in 76ms without hanging the server."*

---

### Q3: "Real festival CSV data is notoriously messy. How does FestOS handle missing, malformed, or conflicting fields?"
> **Answer:**  
> *"We treat `UNKNOWN` as a first-class operational state, never as `NULL` or empty string.  
> If a participant’s dietary preference is blank, FestOS never assumes vegetarian. It tracks the field as UNKNOWN and provisions a dietary uncertainty buffer. If gender is missing, the system never guesses—it blocks corridor assignment until verified.  
> Furthermore, we built the **Unknowns Burn-Down Queue**, which ranks missing fields by operational criticality $\times$ affected count. For high-priority gaps, organizers can generate cryptographically signed one-time verification links to contingent leaders to resolve unknowns asynchronously."*

---

### Q4: "How do you enforce privacy and DPDP compliance when hundreds of student volunteers are operating desks?"
> **Answer:**  
> *"Through gateway-level serializer masking and strict role isolation.  
> Volunteers only see the **Volunteer Mobile View**: two flows (Check-In and Merchandise) with large buttons and zero sensitive personal data. They see the student’s name and contingent, but phone numbers, email addresses, medical notes, and room allocations are completely stripped before leaving the backend API.  
> If an organizer requires sensitive data during an emergency, they must invoke **Break-Glass Elevation**, entering a mandatory justification that creates an immutable, SHA-256 chained audit record."*

---

### Q5: "What happens if two organizers attempt concurrent conflicting mutations—for example, allocating the same remaining room or issuing merchandise?"
> **Answer:**  
> *"FestOS implements two layers of concurrency defense:  
> 1. **Optimistic Version Checks (`expected_version`):** Every mutation routes through our centralized `ChangeService`. If Organizer B submits an assignment on Room 102 with version 1 after Organizer A has already bumped it to version 2, Organizer B immediately receives an HTTP `409 VERSION_CONFLICT` with the fresh state delta.  
> 2. **Database Integrity Constraints:** For merchandise distribution, SQLite enforces `UNIQUE(canonical_participant_id, item_id)`. Even under parallel race conditions, exactly one issuance commits, and the second scan triggers an immediate `409 ALREADY_ISSUED` alert displaying the original desk, volunteer, and timestamp."*

---

### Q6: "What did AI actually do in your solution, and what did your team engineer?"
> **Answer:**  
> *"We maintain strict architectural boundaries under our principle: **AI proposes. Deterministic logic validates. Humans approve.**  
> - **What AI Did:** AI assisted in rapid code boilerplate generation, test case scaffolding, synthetic data analysis, and natural-language regex command parsing (e.g., mapping *'Show the impact of closing Hostel C'* to structured parameters).  
> - **What the Team Engineered:** The entire domain architecture, the 32-module service layer, the ChangeService transaction engine, the three accommodation algorithms, the 10-conflict schedule detector, the cryptographic audit hash chain, and the PWA IndexedDB offline queue. No operational change ever commits to the database without deterministic validation and human sign-off."*

---

### Q7: "What would you build next if given another week?"
> **Answer:**  
> *"Three specific enterprise extensions:  
> 1. **Automated WhatsApp / SMS Gateway Integration:** Wire our notification draft engine into Twilio or Gupshup for live contingent leader broadcasts.  
> 2. **Live GPS Telematics for Shuttles:** Replace the assumed 25-minute shuttle travel windows with live OBD-II vehicle tracking across the campus-resort corridor.  
> 3. **Distributed Multi-Region Master:** Migrate the single SQLite WAL database to a distributed CockroachDB / Postgres cluster for zero-downtime failover across campus Wi-Fi outages."*

---

## Part 3: Tactical Plan for Judges Injecting an Unplanned Disruption

If a judge says: *"What if I want to simulate an unplanned disaster, like heavy rain shutting down the Amphitheatre or a sudden generator blowout?"*

1. **Step 1:** Open the **Disruption Console** (`/incidents`) or press `Ctrl+K` for the **AI Command Center**.
2. **Step 2:** Type the judge's scenario or click **Venue Relocation / Equipment Failure**.
3. **Step 3:** Click **Preview Impact (Dry Run)**:
   - Point out that the live production database is untouched.
   - Show the blast radius: affected stage sessions, audience capacity deficit, and schedule turnover windows.
4. **Step 4:** Open the **Scenario Simulator** (`/scenarios`) $\rightarrow$ Click **Fork Live Database**:
   - Demonstrate a complete sandbox copy where the recovery plan is applied and side-by-side metrics are benchmarked against production.
5. **Step 5:** Click **Discard Scenario**:
   - Prove that the sandbox is destroyed cleanly without leaving any orphan records in live operations.
