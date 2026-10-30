---
marp: true
theme: default
paginate: true
header: 'FestOS — Aarohan 2026 Operations Command Center'
footer: 'EPINOIA 2026 Master Pitch'
---

# FestOS
## The Command Center for Festival Resilience

**Aarohan 2026 (EPINOIA, IIM Indore)**

- **Scale:** 2,836 Participants · 38 Contingents · 31 Events · 1,450 Beds
- **Principle:** AI proposes. Deterministic logic validates. Humans approve.
- **Architectural Guarantee:** Every change updates downstream subsystems.

---

# 1. The Operational Reality (0:00 – 0:45)
### Why Spreadsheets and WhatsApp Groups Collapse

- **Disconnected Silos:** When a contingent arrives 3 hours late, housing doesn't know, transport doesn't wait, and kitchens throw away food.
- **Silent Dropped Records:** The festival prospectus said ~2,400. Real CSVs contain 2,836. Spreadsheets silently drop the 436 excess.
- **Cascading Blindspots:** A flooded hostel displaced 85 students—affecting beds, bus shuttles, dining tokens, and stage schedules.

---

# 2. Data Reconciliation & Quality (0:45 – 1:45)
### Never Force 2,400: The Golden Headcount Waterfall

- **2,400** Primary portal registrations deduped.
- **436** Late contingent entrants verified.
- **426** Unexplained Remainder surfaced in the audit waterfall for committee review.
- **Zero Silent Merges:** 12 candidate duplicates flagged with side-by-side comparison.
- **Quarantine Ledger:** 3 malformed rows quarantined without crashing the database.
- **Tri-State Governance:** `UNKNOWN` is a first-class value, never assumed as NULL or vegetarian.

---

# 3. Transparent Accommodation (1:45 – 3:00)
### Three Deterministic Plans (A, B, and C)

- **Plan A (Cohesion-First):** Keeps college teams together in contiguous wings. 100% cohesion; +₹42,500 external resort cost.
- **Plan B (Cost-First):** Minimizes external spend (+₹21,000) by scattering students into remnant beds. Cohesion drops 38%.
- **Plan C (Balanced):** Weighted equilibrium (50% cohesion, 30% cost, 20% travel proximity).
- **The "Why-not?" Innovation:** Explains exact bottleneck reasons for unplaced participants (e.g. 180-min cleaning buffer or ground-floor wheelchair requirement).

---

# 4. Live Disruption Management (3:00 – 4:30)
### Hostel 3 Plumbing Failure: 85 Beds Evacuated Live

1. **Sub-second Dry Run:** Calculates blast radius in 76ms (85 beds, 2 heats, 7 shuttle loops).
2. **Multi-Plan Comparison:** Side-by-side trade-offs between Plan A and Plan B.
3. **ConfirmWithReason:** Mandatory operational rationale enforced before authorization.
4. **ChangeService Transaction:** Real database commitment and downstream subsystem synchronization.
5. **Interactive Impact Tree:** Visual blast radius tree from root incident down to individual participant nodes.

---

# 5. Scheduling, Inventory & Vendors (4:30 – 5:30)
### Operational Integrity Under Live Event Pressure

- **10 Conflict Types:** Evaluates volunteer fatigue, camera shortages, judge transit, and stage sound bleed—not just venue overlaps.
- **Physical Inventory Math:** Double-entry ledger prevents double-counting in-transit or damaged gear.
- **Merchandise Fraud Shield:** Hard DB constraint `UNIQUE(participant_id, item_id)` rejects repeat QR scans with `409 ALREADY_ISSUED`.
- **Vendor Dietary Fallback:** Real-time tracking of Jain, Vegan, and Gluten-Free slot coverage; sudden vendor health violations reallocated to FSSAI-compliant backup stalls.

---

# 6. Zero-Trust Security & Offline PWA (5:30 – 6:15)
### Resilience When Campus Wi-Fi Drops

- **9 Operational Roles:** Strict RBAC; volunteers have zero access to budgets or personal data.
- **Break-Glass Emergency Protocol:** Emergency unmasking requires justification and writes an indelible cryptographic SHA-256 audit entry.
- **PWA Offline Tolerance:** Check-in and merchandise scans buffer safely into IndexedDB (Dexie).
- **Idempotent Sync:** Reconnect automatically executes `/sync` with exactly-once commitment, safely ignoring duplicates.

---

# 7. Assumptions & AI Disclosure (6:15 – 7:00)
### Honest Engineering & The 0.08s Reset Guarantee

- **Assumptions Register:** 180-minute cleaning buffer, 12-seat shuttle capacity, and 18-year minor threshold are explicit, sourced, and editable.
- **AI Boundaries:** AI proposes suggestions and parses natural language. Deterministic algorithms validate hard constraints. Humans authorize changes.
- **Instant Rehearsal:** `make reset-demo` returns the entire platform to a pristine baseline snapshot in **0.08 seconds**.
