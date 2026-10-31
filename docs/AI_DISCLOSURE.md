# FestOS AI Disclosure & Engineering Boundary (`docs/AI_DISCLOSURE.md`)

> **Festival:** Aarohan (EPINOIA 2026, IIM Indore)  
> **Core Principle:** **AI proposes. Deterministic logic validates. Humans approve.**  
> Artificial intelligence is used as an operational multiplier for repetitive synthesis and assistive reasoning, but is strictly quarantined from making unverified operational mutations or autonomous overrides.

---

## 1. The Three-Column AI Governance Matrix

The following three-column disclosure is presented on the dedicated AI slide during the pitch presentation:

| Column 1: What AI Did | Column 2: What the Team Decided | Column 3: How Outputs Were Checked |
|---|---|---|
| **Code Scaffolding & Architecture**<br>Generated initial boilerplate, FastAPI router skeletons, SQLModel schemas, and Pydantic validation envelopes across 32 modules. | **Constraint Hierarchy Order**<br>Established strict immutable rules: hard constraints (safety, privacy, accessibility) can NEVER be auto-relaxed; soft constraints (cohesion, cost, proximity) require recorded rationale. | **Unit & Property Tests**<br>224 backend tests and 59 frontend tests passing in CI; Hypothesis property-based testing asserting concurrency invariance. |
| **Test Generation**<br>Synthesized end-to-end edge-case test suites, mock requests, fixture generation, and API schema regression tests. | **UNKNOWN-First Semantics**<br>Mandated that `UNKNOWN` is a first-class state. A blank never means vegetarian, male, or absence of special accessibility need. | **Hand-Calculated Benchmarks**<br>Pre-calculated bed demands (710 campus + 740 external = 1,450 beds), minor headcounts (279), and meal slot capacity totals to verify solver math. |
| **Data Quality & Synthesis**<br>Analyzed raw CSV anomalies, flagged 3 invalid datetime intervals, and surfaced 312 duplicate candidate clusters using string metric distance. | **Human Approval Gates**<br>High-risk mutations (hostel block closure, vendor shutdown, budget ceiling overrides) require explicit multi-role human approval. | **Deterministic Constraint Validation**<br>Pure Python constraint engine checks room capacities, gender separation, and cleaning buffers after every proposed plan. |
| **Natural-Language Commands**<br>Interpreted operational search queries and command bar inputs into structured intent filters and entity navigation routes. | **Zero-Trust Privacy & DPDP**<br>Designed serializer-level field masking for phone numbers, emails, medical notes, and room allocations with 15-minute break-glass limits. | **Comparative Plan Review**<br>Human committee review of competing recovery plans (Plan A Cohesion vs. Plan B Cost vs. Plan C Balanced) side-by-side. |
| **Draft Communications**<br>Generated contextual message templates across 5 stakeholder audiences (contingent leaders, volunteers, vendors, coordinators, organisers). | **Audit Hash-Chain Architecture**<br>Designed append-only SQLite audit ledger with cryptographic SHA-256 hash-chaining (`prev_hash`, `current_hash`) and tamper triggers. | **Manual Audit of Flagged Records**<br>100% human inspection of all duplicate candidates and quarantined invalid records before database promotion. |

---

## 2. Deep Dive: Architectural Boundaries

### 2.1 Where AI is Prohibited
1. **No Autonomous Database Writes:** An LLM or heuristic suggestion cannot directly write to the SQLite database. Every mutation must construct a validated `ChangeRequest` executed by `ChangeService`.
2. **No Constraint Relaxation:** An LLM cannot decide that a wheelchair user may stay in a 2nd-floor walkup room. Such hard constraint overrides require the Festival Director's cryptographically logged sign-off.
3. **No Automatic Merging:** Duplication models suggest potential merges (e.g., similar names or identical contacts), but records are never merged automatically. A human coordinator must review side-by-side attributes.
4. **No Unapproved Dispatches:** Generated notification drafts cannot be transmitted over communication channels without prior review and approval by an authorized coordinator.

### 2.2 Where AI is Leveraged
1. **Attention Prioritization:** Computing the dynamic Attention Score:
   $$\text{Attention Score} = \text{Severity (1–4)} \times \text{Urgency (1–5)} \times \max(\text{People Affected}, 1)$$
   to rank incident queues and alert coordinators to escalating risks.
2. **Value of Information (VoI) Ranking:** Scoring unresolved data unknowns by operational criticality to surface the most valuable questions to contingent leaders first.
3. **Draft Synthesis:** Automatically filling audience-specific notification drafts with exact vendor names, relocated room numbers, and meal compensation vouchers during live disruptions.
4. **Natural-Language Parsing:** Extracting structured filters (e.g. `find vegetarian female participants from C02`) to accelerate coordinator workflow.

---

## 3. Human-in-the-Loop Verification Protocol

Every operational output produced during development and festival runtime followed a 4-tier verification protocol:

```text
+-----------------------+     +------------------------+     +------------------------+     +------------------------+
| 1. Pure Engine Logic  | --> | 2. Deterministic Check | --> | 3. Explainability Card | --> | 4. Human Sign-Off      |
| AI / Heuristic drafts |     | Unit & property tests  |     | Why Card details risks |     | Role-authorized human  |
| candidates & plans    |     | validate constraints   |     | and alternatives       |     | commits via ChangeSet  |
+-----------------------+     +------------------------+     +------------------------+     +------------------------+
```

1. **Automated Continuous Verification:**
   - `scripts/smoke_all.py` runs all 32 modules and 7 live disruption drills.
   - `scripts/check_cross_module_consistency.py` verifies read-only public contracts across all modules.
   - `scripts/verify_claims.py` validates that all numbers quoted in documentation match live database rows.
2. **Deterministic Constraint Guardrails:**
   - 10 scheduling conflict types (room overlap, travel buffer deficits, volunteer fatigue).
   - Accommodation constraints (gender segregation, 180-min cleaning buffer, wheelchair access).
   - Inventory equations (total quantity = available + issued + reserved + maintenance).
3. **Decision Cards (`DecisionCard`):**
   - Every significant operational choice stores the rationale, alternatives rejected, cost delta, and approving actor.
