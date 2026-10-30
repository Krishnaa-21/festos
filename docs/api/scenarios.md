# API Specification: `scenarios`

> Owner: `P1`  
> Base Path: `/api/v1/scenarios`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Scenario Simulator / Sandbox Engine** empowers festival organizers to safely test operational disruptions, evaluate alternative plans, and analyze blast radius impact without modifying live operational data.

Key architectural principles:
- **Sandbox Database Isolation**:
  - **SQLite Live Engine**: When a scenario is created, the system forks the live database into an isolated sandbox file (`scenarios/<id>.db`) using SQLite `VACUUM INTO` (or atomic copy).
  - **PostgreSQL Alternative**: In a PostgreSQL deployment, the engine creates an isolated schema (`CREATE SCHEMA scenario_<id>`) copying live tables, or provisions a temporary branch database via copy-on-write storage.
  - All database queries for the scenario are scoped using `app.core.db.use_scenario(scenario_id)` via Python `ContextVar`.
- **In-Sandbox Disruption Execution**:
  - Organizers apply hypothetical disruptions (e.g. hostel closure, vendor cancellation, equipment breakdown) directly inside the sandbox using standard ChangeService actions.
- **Metric Diffs & Comparison (`/compare`)**:
  - Calculates side-by-side metric diffs between live production state and the simulated sandbox across:
    - Available & occupied beds
    - Unplaced participants
    - Operational & external accommodation costs
    - Schedule conflicts and judge coverage
    - Vendor food coverage and meal deficits
    - Total high-risk items
- **Safe Replay & Rebase Commit (`/commit`)**:
  - Once verified and approved by the Festival Director, recorded scenario changes are replayed against the live database through ChangeService.
  - **Rebase Check**: If the live database state has mutated since the scenario was forked, the system warns operators of potential divergence before committing.
- **Lifecycle & Cleanup (`/discard`)**:
  - Scenarios can be safely discarded, cleaning up database files.
  - Enforces retention quotas: max 10 concurrent active scenarios and automatic cleanup after 48 hours.
- **Incident Simulation Adapter**:
  - Provides a direct programmatic adapter (`simulate_incident_in_scenario`) for Prompt 14 and crisis response drills.

---

## 2. Endpoints

### 2.1 `POST /api/v1/scenarios`
- **Description**: Forks the live production database into an isolated sandbox environment.
- **Request Body**:
```json
{
  "name": "Hostel B Flooding Simulation",
  "description": "Simulates 120-bed hostel closure and tests external property spillover options."
}
```
- **Response `201 Created`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "name": "Hostel B Flooding Simulation",
    "status": "DRAFT",
    "created_at": "2026-10-31T01:15:00Z",
    "forked_at": "2026-10-31T01:15:00Z",
    "sandbox_url": "sqlite:///./scenarios/scn_a1b2c3d4.db",
    "rebase_baseline_changesets": 42
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/scenarios`
- **Description**: Lists active, committed, and discarded simulation scenarios.
- **Query Parameters**:
  - `status` (string, optional: `DRAFT`, `COMMITTED`, `DISCARDED`)
- **Response `200 OK`**:
```json
{
  "data": {
    "scenarios": [
      {
        "id": "scn_a1b2c3d4",
        "name": "Hostel B Flooding Simulation",
        "status": "DRAFT",
        "created_by": "usr_director",
        "created_at": "2026-10-31T01:15:00Z",
        "actions_count": 2
      }
    ],
    "total": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/scenarios/{id}`
- **Description**: Returns scenario details, metadata, and recorded actions.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "scn_a1b2c3d4",
    "name": "Hostel B Flooding Simulation",
    "description": "Simulates 120-bed hostel closure",
    "status": "DRAFT",
    "created_by": "usr_director",
    "created_at": "2026-10-31T01:15:00Z",
    "recorded_actions": [
      {
        "action": "accommodation.close_hostel",
        "entity_id": "HST02",
        "payload": { "hostel_id": "HST02", "reason": "Water pipe leak" }
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/scenarios/{id}/actions`
- **Description**: Executes a ChangeService mutation inside the isolated scenario sandbox.
- **Request Body**:
```json
{
  "action": "accommodation.close_hostel",
  "entity_type": "hostel",
  "entity_id": "HST02",
  "payload": {
    "hostel_id": "HST02",
    "reason": "Water pipe leak in Block B"
  },
  "reason": "Simulated infrastructure failure"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "action": "accommodation.close_hostel",
    "status": "APPLIED_IN_SANDBOX",
    "result": {
      "beds_deactivated": 120,
      "displaced_participants": 84
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/scenarios/{id}/compare`
- **Description**: Computes metrics diff comparing live production state versus the simulated sandbox state.
- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "live_state": {
      "available_beds": 312,
      "unplaced_participants": 0,
      "cost_inr": 120000.0,
      "conflicts_count": 3,
      "high_risks_count": 2
    },
    "simulated_state": {
      "available_beds": 192,
      "unplaced_participants": 48,
      "cost_inr": 159600.0,
      "conflicts_count": 3,
      "high_risks_count": 4
    },
    "diff": {
      "beds_delta": -120,
      "unplaced_delta": 48,
      "cost_delta_inr": 39600.0,
      "conflicts_delta": 0,
      "risks_delta": 2
    },
    "summary": "Closing Hostel B displaces 48 participants and increases external accommodation costs by ₹39,600."
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `POST /api/v1/scenarios/{id}/commit`
- **Description**: Replays all recorded sandbox changes onto the live production database through ChangeService after Director sign-off.
- **Request Body**:
```json
{
  "reason": "Director approved spillover plan to Lakeview Hotel following confirmed pipe repair timeline."
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "status": "COMMITTED",
    "replayed_actions_count": 2,
    "rebase_status": "CLEAN",
    "live_changesets_created": [
      "cs_replay_01",
      "cs_replay_02"
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/scenarios/{id}/discard`
- **Description**: Discards scenario and purges sandbox storage.
- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "status": "DISCARDED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `POST /api/v1/scenarios/{id}/simulate-incident`
- **Description**: Incident simulation adapter allowing Prompt 14 incident response drills to simulate real-time crises inside a sandbox.
- **Request Body**:
```json
{
  "incident_type": "HOSTEL_CLOSURE",
  "target_id": "HST02",
  "severity": 4,
  "details": "Major water pipe burst affecting all floors of Hostel B"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scn_a1b2c3d4",
    "incident_id": "inc_sim_01",
    "status": "SIMULATED",
    "impact": {
      "affected_people": 84,
      "immediate_actions_required": [
        "Reallocate 84 residents to external properties",
        "Dispatch 6 shuttle runs"
      ]
    }
  },
  "meta": {},
  "warnings": []
}
```
