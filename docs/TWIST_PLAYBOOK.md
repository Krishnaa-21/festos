# FestOS Twist Playbook: Handling Surprises, Drills, and Hour-12 Injections

> **Audience**: FestOS Engineering Core, Operational Leads, and Incident Commanders.  
> **Purpose**: A deterministic, step-by-step technical guide for extending FestOS under high-pressure live conditions (e.g. the Hour-12 Twist, live evaluation disruptions, and judge surprise parameters).  
> **Guiding Principle**: *No panic, no hacks, no contract drift.* Every surprise maps to one of six established extension points.

---

## 1. Quick Decision Matrix

When a surprise or twist is declared, identify its archetype immediately:

| Twist Archetype | Extension Vector | Primary Code Files | Testing Strategy |
|---|---|---|---|
| *"New non-negotiable rule announced"* | **Vector 1: Hard Constraint** | `backend/app/engines/`, `app/core/change_service.py` | Unit test violation (422) + ladder check |
| *"New crisis / scenario injected"* | **Vector 2: Disruption Type** | `backend/app/services/scenarios/`, Change Handlers | Sandbox isolation + rollback + audit test |
| *"Organizer requests new summary export"* | **Vector 3: Operational Report** | `backend/app/services/reports/` | Golden CSV fixture + schema validation |
| *"New operational buffer or rule variable"*| **Vector 4: Assumption Key** | `backend/app/models/change.py`, `app/seed/assumptions.py` | Audited mutation + cascade alert |
| *"New attendee metadata field provided"* | **Vector 5: Participant Attribute** | `backend/app/models/participants.py`, `app/core/masking.py` | Role masking test + importer update |
| *"New committee or stakeholder introduced"* | **Vector 6: Operational Role** | `backend/app/schemas/common.py`, `app/core/rbac.py` | Permission matrix check + 403 test |

---

## 2. Vector 1: Adding a New Hard Constraint

### Context
A requirement is introduced that must reject invalid operations (e.g., *"No team from college X may share a floor with college Y"* or *"Curfew at 21:00 instead of 22:00"*).

### Step-by-Step Implementation
1. **Define the Constraint Code & Violation**:
   - Open `backend/app/schemas/common.py` or the relevant engine schema.
   - Assign a unique violation code (e.g., `CURFEW_BREACH`, `RIVALRY_SEPARATION_VIOLATED`).
2. **Implement in Pure Engine**:
   - Location: Pure allocation engine (`backend/app/engines/accommodation/allocator.py` or `schedule/engine.py`).
   - Implement as a deterministic validator function:
     ```python
     def check_rivalry_constraint(participant_a, participant_b) -> Optional[Violation]:
         if participant_a.college in RIVAL_PAIRS.get(participant_b.college, []):
             return Violation(
                 code="RIVALRY_SEPARATION_VIOLATED",
                 severity=4,
                 hard=True,
                 message=f"Rival colleges {participant_a.college} and {participant_b.college} cannot share room"
             )
         return None
     ```
3. **Register in ChangeService Handler**:
   - In `backend/app/services/<module>/handlers.py`, add the check to `validate()`:
     ```python
     def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
         violations = []
         # Check constraint
         if violation := check_rivalry_constraint(...):
             violations.append(violation)
         return violations
     ```
4. **Wire to Constraint Relaxation Ladder**:
   - If the constraint can be relaxed by Director break-glass, register it in `backend/app/core/scoring.py` with its penalty weight.

### Tests to Add
- Add test in `backend/tests/<module>/test_constraints.py`:
  - Assert mutation is rejected with `status == "REJECTED"` and violation code present.
  - Assert that relaxing the constraint allows placement with an active override and audit event.

---

## 3. Vector 2: Adding a New Disruption Type

### Context
A major operational disruption occurs (e.g., *"Heavy rain floods Amphitheatre"* or *"Catering vendor V04 food poisoning investigation"*).

### Step-by-Step Implementation
1. **Create Change Handler**:
   - Open `backend/app/services/scenarios/handlers.py` or domain `handlers.py`.
   - Register a new change handler:
     ```python
     @register_change_handler("venue.flood_closure")
     class VenueFloodClosureHandler(ChangeHandler):
         def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
             return []
         def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
             venue = session.get(Venue, req.entity_id)
             return {"status": venue.status} if venue else {}
         def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
             venue = session.get(Venue, req.entity_id)
             venue.status = "FLOODED"
             session.add(venue)
             session.flush()
             return {"venue_id": venue.id, "new_status": "FLOODED"}
     ```
2. **Wire to Scenario Sandbox**:
   - In `backend/app/services/scenarios/service.py` inside `simulate_incident_in_scenario`:
     ```python
     elif "FLOOD" in incident_type.upper():
         # Re-route sessions to indoor backup venues
         ...
     ```
3. **Test in Sandbox Before Committing**:
   - Call `POST /api/v1/scenarios` (forks live DB).
   - Execute mutation inside sandbox via `POST /api/v1/scenarios/{id}/actions`.
   - Inspect diff via `GET /api/v1/scenarios/{id}/compare`.
   - Commit onto production via `POST /api/v1/scenarios/{id}/commit`.

### Tests to Add
- Add test in `backend/tests/scenarios/test_scenario_sandbox.py`:
  - Assert sandbox mutation does not touch live database until committed.
  - Assert live commit produces immutable audit trail.

---

## 4. Vector 3: Adding a New Operational Report

### Context
Jury or festival leadership requests a brand new operational breakdown (e.g., *"Special Dietary Logistics Report"* or *"External Transport Fuel & Toll Audit"*).

### Step-by-Step Implementation
1. **Create Report Generator**:
   - Location: `backend/app/services/reports/`
   - Create `backend/app/services/reports/generators/<new_report>.py`:
     ```python
     def generate_fuel_audit_csv(session: Session) -> str:
         output = io.StringIO()
         writer = csv.writer(output)
         writer.writerow(["shuttle_id", "route", "trips", "estimated_fuel_litres", "cost_inr"])
         # Query shuttles and write rows
         ...
         return output.getvalue()
     ```
2. **Register Generator**:
   - In `backend/app/services/reports/service.py`:
     - Add report slug to `REPORT_REGISTRY`:
       ```python
       REPORT_REGISTRY["fuel_audit"] = {
           "name": "External Transport Fuel & Toll Audit",
           "filename": "fuel_audit.csv",
           "generator": generate_fuel_audit_csv,
           "permission": "transport:read"
       }
       ```
3. **Automatic Bundle Inclusion**:
   - The report is automatically exposed at `GET /api/v1/reports/fuel_audit` and bundled inside `GET /api/v1/reports/bundle.zip`.

### Tests to Add
- Add test in `backend/tests/reports/test_reports.py`:
  - Assert `GET /api/v1/reports/fuel_audit` returns 200 with `text/csv` and correct headers.

---

## 5. Vector 4: Adding a New Assumption Key

### Context
A key numerical threshold or policy assumption changes dynamically (e.g., *"Change room cleaning buffer from 45 mins to 60 mins"* or *"New fuel price multiplier"*).

### Step-by-Step Implementation
1. **Define Assumption Metadata**:
   - Open `backend/app/seed/assumptions.py`.
   - Add new entry:
     ```python
     {
         "key": "fuel_price_per_litre_inr",
         "value": 105.5,
         "data_type": "FLOAT",
         "description": "Commercial diesel price benchmark for external shuttles",
         "category": "TRANSPORT",
         "impact_scope": "transport,finance"
     }
     ```
2. **Register in Public Contract**:
   - In `backend/app/services/assumptions/public.py`, register the key in default fallback list.
3. **Use in Service Logic**:
   - Query through `get_assumption(session, "fuel_price_per_litre_inr")`.
4. **Live Mutation**:
   - Update via `PUT /api/v1/assumptions/fuel_price_per_litre_inr` with mandatory reason.

### Tests to Add
- Assert that modifying the assumption creates a change event and invalidates cached calculations.

---

## 6. Vector 5: Adding a New Participant Attribute

### Context
Organizers introduce a new participant flag (e.g., *"VIP_GUEST"*, *"FAST_TRACK_REGISTRATION"*, or *"ALLERGY_MEDICATION_NOTES"*).

### Step-by-Step Implementation
1. **Update SQLModel Schema**:
   - Location: `backend/app/models/participants.py`
   - Add column with safe default:
     ```python
     is_vip: bool = Field(default=False)
     medication_notes: Optional[str] = Field(default=None)
     ```
2. **Configure Masking Rules**:
   - If the field contains private/medical details:
     - Open `backend/app/core/masking.py`.
     - Add field name to `SENSITIVE_FIELDS`:
       ```python
       SENSITIVE_FIELDS.add("medication_notes")
       ```
     - Only authorized roles (`FESTIVAL_DIRECTOR`, medical lead) or break-glass callers can view raw values.
3. **Update Importer Mapping**:
   - If present in incoming CSV, update `data/mapping/participants.json` column mapping.

### Tests to Add
- Add test in `backend/tests/participants/test_participants.py`:
  - Assert unauthorized roles receive masked value `***`.
  - Assert break-glass elevates field access and logs an audit event.

---

## 7. Vector 6: Adding a New Operational Role

### Context
A new specialized operational role is introduced (e.g., *"SAFETY_OFFICER"*, *"STAGE_MANAGER"*).

### Step-by-Step Implementation
1. **Update Role Enum**:
   - Location: `backend/app/schemas/common.py`
   - Add value to `Role(str, Enum)`:
     ```python
     class Role(str, Enum):
         ...
         SAFETY_OFFICER = "SAFETY_OFFICER"
     ```
2. **Configure RBAC Permissions Matrix**:
   - Location: `backend/app/core/rbac.py`
   - Add permissions in `ROLE_PERMISSIONS`:
     ```python
     Role.SAFETY_OFFICER.value: {
         "incidents:read", "incidents:write",
         "venues:read", "schedule:read",
         "audit:read"
     }
     ```
3. **Seed Test User**:
   - In `backend/app/seed/users.py`, add demo credentials for testing:
     ```python
     {
         "email": "safety@festos.internal",
         "raw_password": "FestOSSafety2026!",
         "role": Role.SAFETY_OFFICER.value,
         "full_name": "Safety Lead"
     }
     ```
4. **Update Frontend UI**:
   - Add role to `frontend/src/features/auth/LoginPage.tsx` quick switcher.

### Tests to Add
- Add test in `backend/tests/test_security_p3.py`:
  - Verify new role can access allowed endpoints and receives 403 on disallowed endpoints.

---

## 8. The 15-Minute Hour-12 Twist Protocol

When the live twist is announced during evaluation:
1. **Minute 0–2: Classify & Formulate**:
   - Identify which vector(s) apply.
   - Formulate exact change request payload.
2. **Minute 3–7: Implement in Branch**:
   - Follow the vector steps above.
   - Run unit test for that specific file: `pytest backend/tests/<module>/test_*.py`.
3. **Minute 8–11: Run Smoke & Consistency Suite**:
   - Run `python scripts/check_cross_module_consistency.py`.
   - Run `python scripts/smoke_all.py`.
4. **Minute 12–15: Demonstrate Live to Evaluators**:
   - Show the Change Request.
   - Show the blast radius impact.
   - Show the before/after state comparison.
   - Show the immutable audit event in `/api/v1/audit/events`.
