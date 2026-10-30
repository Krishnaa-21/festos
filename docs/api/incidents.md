# API Specification: `incidents`

> Owner: `P2`  
> Base Path: `/api/v1/incidents`  
> Status: `ACTIVE`

---

## 1. Overview
The **Incident Command & Disruption Orchestration Engine** (spec sections 6.1, 6.6, 12.5, 13, and 8) acts as FestOS's central intelligence layer. Any operational disruption, failure, or injected scenario yields:
1. Downstream blast radius analysis via the dependency graph (`engines/impact`).
2. Two or more ranked minimal-change recovery plans (`engines/replan`) comparing trade-offs:
   - People moved / relocated
   - Schedule disruption / delays
   - Resource & equipment movement
   - Contingent cohesion preservation
   - Net cost impact / variance (INR)
   - Draft notifications across all 5 audiences (`Prompt 11 / notifications.service.generate_drafts`)
3. Human approval via the core approvals framework (`approvals.require` / `Role.FESTIVAL_DIRECTOR`).
4. Real state updates applied via `core.change_service` (asserted in real DB rows).
5. Post-execution verification re-running module risks and showing before/after resolution state.

### Incident Lifecycle
```text
OPEN ──> ANALYSING ──> PLAN_PROPOSED ──> APPROVED ──> EXECUTING ──> VERIFIED ──> CLOSED
```

### Seven Mandatory Live-Test Scenarios
- `LATE_CONTINGENT`: Update arrival timestamps, run `allocate_incremental`, recheck sessions, meals, merch entitlements, transport demand.
- `DUPLICATE_PARTICIPANT`: Call reconciliation merge/undo, repoint registrations, stay assignments, claims, show affected reservations.
- `HOSTEL_CLOSURE`: Call accommodation minimal-change replan, show affected participants, cost delta, accessibility/minor safety flags.
- `EQUIPMENT_FAILURE`: Analyze dependent event sessions, evaluate alternative units with transfer feasibility and reschedule options.
- `VENUE_CHANGE`: Recheck capacity, timing, participants, travel, and resource constraints; rank alternatives.
- `VENDOR_SHUTDOWN`: Call `vendor_shutdown_analysis`, identify dietary gaps, rank replacements, cost delta, notification drafts.
- `DUPLICATE_MERCHANDISE_CLAIM`: Reject duplicate claim attempt, show original claim transaction, flag suspected duplicate identity.
- *Extras*: `BUS_DELAY`, `STAFF_SHORTAGE`, `VENUE_UNAVAILABLE`, `EVENT_CANCELLED`, `ROOM_UNAVAILABLE`, `DEMAND_SURGE`, `CERTIFICATE_EXPIRY`.

---

## 2. Endpoints

### 2.1 `GET /api/v1/disruptions/catalog`
- **Description**: Returns all disruption scenarios, parameter schemas, target entity types, and simulation metadata.
- **Aliases**: `/api/v1/disruptions/catalog`, `/api/v1/incidents/catalog`
- **Response `200 OK`**:
```json
{
  "data": {
    "scenarios": [
      {
        "scenario_type": "LATE_CONTINGENT",
        "title": "Late Contingent Arrival",
        "description": "Contingent arrival delayed past scheduled check-in window and event start times.",
        "parameters_schema": {
          "contingent_id": {"type": "string", "required": true, "example": "CONT_DELHI"},
          "delay_hours": {"type": "number", "required": true, "default": 3.0}
        }
      },
      {
        "scenario_type": "DUPLICATE_PARTICIPANT",
        "title": "Duplicate Participant Ingestion",
        "description": "Cross-college duplicate or multi-registration identity requiring merge or separation.",
        "parameters_schema": {
          "primary_id": {"type": "string", "required": true},
          "duplicate_id": {"type": "string", "required": true}
        }
      },
      {
        "scenario_type": "HOSTEL_CLOSURE",
        "title": "Hostel / Block Closure",
        "description": "Plumbing or electrical failure closes an on-campus hostel block requiring resident relocation.",
        "parameters_schema": {
          "block": {"type": "string", "required": true, "example": "Hostel C"},
          "reason": {"type": "string", "required": true}
        }
      },
      {
        "scenario_type": "EQUIPMENT_FAILURE",
        "title": "Critical Equipment Failure",
        "description": "AV, sound, or projection gear fails at an active event venue.",
        "parameters_schema": {
          "equipment_id": {"type": "string", "required": true},
          "venue_id": {"type": "string", "required": true}
        }
      },
      {
        "scenario_type": "VENUE_CHANGE",
        "title": "Emergency Venue Change",
        "description": "Unscheduled maintenance forces event relocation to an alternative venue.",
        "parameters_schema": {
          "event_id": {"type": "string", "required": true},
          "target_venue_id": {"type": "string", "required": false}
        }
      },
      {
        "scenario_type": "VENDOR_SHUTDOWN",
        "title": "Vendor Hygiene / Health Shutdown",
        "description": "Health inspector shuts down catering vendor; reallocates slots and meals.",
        "parameters_schema": {
          "vendor_id": {"type": "string", "required": true, "example": "VND03"},
          "from_time": {"type": "string", "required": false}
        }
      },
      {
        "scenario_type": "DUPLICATE_MERCHANDISE_CLAIM",
        "title": "Duplicate Merchandise Claim Attempt",
        "description": "Tests double-scan rejection, audits original claim, and flags duplicate identity.",
        "parameters_schema": {
          "participant_id": {"type": "string", "required": true}
        }
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `POST /api/v1/incidents`
- **Description**: Injects a disruption or logs an operational incident. Can run in `dry_run` mode to preview downstream impact and recovery plans without state modification.
- **Request Body**:
```json
{
  "scenario_type": "HOSTEL_CLOSURE",
  "title": "Hostel Block C Pipe Burst",
  "severity": "HIGH",
  "entity_type": "hostel",
  "entity_id": "Hostel C",
  "parameters": {
    "block": "Hostel C",
    "reason": "Plumbing pipe burst flooding ground floor"
  },
  "dry_run": false
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "inc_9821a",
    "scenario_type": "HOSTEL_CLOSURE",
    "title": "Hostel Block C Pipe Burst",
    "status": "PLAN_PROPOSED",
    "severity": "HIGH",
    "people_affected": 42,
    "created_at": "2026-10-30T14:00:00Z",
    "timeline": [
      {"status": "OPEN", "timestamp": "2026-10-30T14:00:00Z", "actor": "Ops Lead"},
      {"status": "ANALYSING", "timestamp": "2026-10-30T14:00:01Z", "actor": "ImpactEngine"},
      {"status": "PLAN_PROPOSED", "timestamp": "2026-10-30T14:00:02Z", "actor": "ReplanEngine"}
    ],
    "impact_summary": {
      "total_entities_affected": 56,
      "people_affected": 42,
      "severities": {"CRITICAL": 0, "HIGH": 12, "MEDIUM": 30, "LOW": 14}
    },
    "recovery_plans_count": 2
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/incidents`
- **Description**: Lists recorded incidents with status, severity, and pagination filters.
- **Query Parameters**: `status`, `severity`, `scenario_type`, `limit`, `offset`.

---

### 2.4 `GET /api/v1/incidents/{id}`
- **Description**: Returns detailed incident record with full audit timeline, blast radius summary, approved plan, and resolution status.

---

### 2.5 `GET /api/v1/incidents/{id}/impact`
- **Description**: Returns the full hierarchical blast radius impact tree for the incident, with node statuses (`PENDING`, `UPDATED`, `VERIFIED`).

---

### 2.6 `GET /api/v1/incidents/{id}/plans`
- **Description**: Compares two or more generated recovery plans across trade-off dimensions.
- **Response `200 OK`**:
```json
{
  "data": {
    "incident_id": "inc_9821a",
    "plans": [
      {
        "plan_id": "plan_alpha",
        "rank": 1,
        "name": "Cohesion-Preserving Campus Placement",
        "summary": "Relocates 42 students into available campus beds in Hostel A and B.",
        "people_moved": 42,
        "schedule_changes": 0,
        "resource_moves": 0,
        "cost_increase_inr": 0.0,
        "cohesion_score": 92.5,
        "notifications_drafted": 5,
        "requires_director_approval": false
      },
      {
        "plan_id": "plan_beta",
        "rank": 2,
        "name": "Single-Property External Overflow",
        "summary": "Transfers all 42 participants together into Hotel Grand Indore.",
        "people_moved": 42,
        "schedule_changes": 2,
        "resource_moves": 4,
        "cost_increase_inr": 44100.0,
        "cohesion_score": 98.0,
        "notifications_drafted": 5,
        "requires_director_approval": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/incidents/{id}/approve`
- **Description**: Human approver selects and signs off on a candidate recovery plan. Invokes ChangeService handler to execute real mutations.
- **Request Body**:
```json
{
  "plan_id": "plan_alpha",
  "reason": "Prioritizes campus housing and keeps contingent intact without external cost."
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "incident_id": "inc_9821a",
    "status": "EXECUTING",
    "approved_plan_id": "plan_alpha",
    "change_set_id": "cs_inc_9821a_rec",
    "applied_at": "2026-10-30T14:05:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `POST /api/v1/incidents/{id}/verify`
- **Description**: Runs verification pass post-execution. Re-evaluates module risk functions, confirms database state, marks node downstream statuses as `VERIFIED`, and transitions incident to `VERIFIED` or `CLOSED`.
- **Response `200 OK`**:
```json
{
  "data": {
    "incident_id": "inc_9821a",
    "status": "VERIFIED",
    "verified_at": "2026-10-30T14:06:00Z",
    "verification_passed": true,
    "remaining_risks": [],
    "before_after": {
      "unplaced_participants_before": 42,
      "unplaced_participants_after": 0,
      "capacity_deficit_before": 42,
      "capacity_deficit_after": 0
    },
    "decision_card_id": "dec_inc_9821a"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `GET /api/v1/incidents/report/csv`
- **Description**: Downloads `incident_report.csv` containing incident history, MTTR, affected counts, and resolution plans.
