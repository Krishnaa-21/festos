# API Specification: `assumptions`

> Owner: `P2`  
> Base Path: `/api/v1/assumptions`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `assumptions` module manages configurable operational assumptions, baseline parameters, and system heuristics.
Assumptions are visible, editable, owned, sourced, and audited. Every change invalidates cached values and triggers downstream impact tracking.

Key Operations:
- Baseline seeding of all 22+ standard fest assumptions (e.g., cleaning buffer, minor threshold, narrative expected participants, late night hours).
- Typed value validation (integers, floats, times, enums, booleans).
- Mutation through ChangeService handler `assumptions.update` (immutable audit trail and change history).
- Module usage previews to see which downstream systems read an assumption.

---

## 2. Endpoints

### 2.1 `GET /api/v1/assumptions`
- **Description**: List all operational assumptions with their owner, source, reason, impact-if-changed, and current typed value.
- **Query Parameters**:
  - `owner` (string, optional: `P1`, `P2`, `P3`)
  - `q` (string, optional: search in key, reason, or impact)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "asm_01",
        "key": "cleaning_buffer_minutes",
        "value": "180",
        "typed_value": 180,
        "type": "integer",
        "owner": "P2",
        "source": "SPEC",
        "reason": "Turnaround buffer required between hostel bed occupants",
        "impact_if_changed": "Recalculates turnaround and available bed intervals",
        "updated_at": "2026-10-30T13:30:00Z"
      }
    ],
    "total": 24
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `PUT /api/v1/assumptions`
- **Description**: Update an assumption via ChangeService handler `assumptions.update`. Audited and records previous state.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "key": "cleaning_buffer_minutes",
  "value": "120",
  "reason": "Optimized housekeeping schedule with additional cleaning staff",
  "expected_version": 1,
  "dry_run": false
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_asm_upd_01",
    "status": "APPLIED",
    "violations": [],
    "audit_event_ids": ["aud_asm_01"],
    "impact": {
      "key": "cleaning_buffer_minutes",
      "old_value": "180",
      "new_value": "120",
      "dependent_modules": ["accommodation", "schedule"]
    },
    "recommendations": [],
    "warnings": []
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/assumptions/{key}/history`
- **Description**: Retrieve the complete change history and audit trail for a specific assumption key.
- **Path Parameters**:
  - `key`: string (e.g. `cleaning_buffer_minutes`)
- **Response `200 OK`**:
```json
{
  "data": {
    "key": "cleaning_buffer_minutes",
    "history": [
      {
        "change_set_id": "cs_asm_upd_01",
        "actor_id": "usr_director",
        "actor_role": "FESTIVAL_DIRECTOR",
        "previous_value": "180",
        "new_value": "120",
        "reason": "Optimized housekeeping schedule with additional cleaning staff",
        "applied_at": "2026-10-30T13:35:00Z"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/assumptions/{key}/dependents`
- **Description**: Preview which modules and engines consume or depend on this assumption key.
- **Path Parameters**:
  - `key`: string (e.g. `minor_age_threshold`)
- **Response `200 OK`**:
```json
{
  "data": {
    "key": "minor_age_threshold",
    "dependent_modules": [
      "imports",
      "accommodation",
      "transport"
    ],
    "description": "Used by imports validation to flag minor safety issues, by accommodation to prevent placing minors in unverified external stays without escorts, and by transport for curfew checks."
  },
  "meta": {},
  "warnings": []
}
```
