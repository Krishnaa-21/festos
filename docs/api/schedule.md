# API Specification: Event Scheduling & Conflict Detection

> Owner: `P1`  
> Base Path: `/api/v1/schedule`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Schedule module implements pure scheduling logic (`engines/scheduling`), versioning, multi-round heat generation, arrival-wave handling, 10-type conflict detection (sweep-line), unscheduled participant reporting, and resolution recommendation with version rollback. All schedules generated are labelled `ASSUMED`.

---

## 2. Endpoints

### 2.1 `POST /api/v1/schedule/generate`
- **Description**: Generate an ASSUMED schedule plan using pure scheduling engine with constraint checks.
- **Headers**: `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "plan_name": "Plan Alpha - Greedy Graph Clustered",
  "solver": "greedy",
  "include_late_wave": true,
  "wildcard_finals": false,
  "reason": "Initial full fest schedule generation"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "version_id": "sch_123456",
    "plan_name": "Plan Alpha - Greedy Graph Clustered",
    "status": "ASSUMED",
    "total_sessions": 172,
    "scheduled_registrations": 4593,
    "unscheduled_registrations": 987,
    "unplaced_sessions": 28,
    "conflicts_count": 0,
    "fairness_proposals": [
      {
        "id": "prop_late_wave",
        "title": "Late Arrival Wave on 1 Nov morning",
        "status": "PENDING_APPROVAL",
        "requires_role": "FESTIVAL_DIRECTOR",
        "reason": "13% participants arrive late night Oct 31"
      }
    ]
  },
  "meta": {
    "prototype_benchmark": {
      "prototype_sessions": 172,
      "prototype_unscheduled": 987,
      "prototype_unplaced_sessions": 28,
      "prototype_venue_overlaps": 0
    }
  },
  "warnings": [
    "Schedule is labelled ASSUMED. Raw data contains no event times or venue assignments.",
    "987 entrants unscheduled due to arrival window limits or personal clashes."
  ]
}
```

---

### 2.2 `GET /api/v1/schedule/versions`
- **Description**: List all saved schedule versions with session counts and conflict summaries.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "sch_123456",
        "plan_name": "Plan Alpha",
        "status": "ASSUMED",
        "sessions_count": 172,
        "conflicts_count": 0,
        "created_at": "2026-10-30T10:00:00Z"
      }
    ],
    "total": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/schedule/versions/{id}/restore`
- **Description**: Restore a previous schedule version via `ChangeService` action `schedule.restore_version`.
- **Request Body**:
```json
{
  "reason": "Rollback to pre-incident timetable"
}
```

---

### 2.4 `GET /api/v1/schedule/sessions`
- **Description**: Query scheduled sessions with filters. Exposes resource requirements for downstream modules.
- **Query Parameters**:
  - `event_id` (string, optional)
  - `venue_id` (string, optional)
  - `round` (string, optional: `prelims` | `semis` | `finals` | `single`)
  - `wave` (string, optional: `E` | `M` | `L`)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "ses_001",
        "event_id": "E01",
        "event_name": "Aarohan",
        "round": "prelims",
        "heat": "M1",
        "venue_id": "V04",
        "venue_name": "Amphitheatre",
        "start_at": "2026-10-31T08:00:00Z",
        "end_at": "2026-10-31T09:30:00Z",
        "entrants_count": 45,
        "entrant_basis": "registered (assigned)",
        "volunteers_required": 10,
        "equipment_required": "barricades; tables",
        "judge_slots_needed": 2,
        "assigned_judges": []
      }
    ],
    "total": 172
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/schedule/sessions/{id}/move`
- **Description**: Move session time via `ChangeService` action `schedule.move_session`.
- **Request Body**:
```json
{
  "new_start_at": "2026-10-31T10:00:00Z",
  "reason": "Resolved rain delay",
  "expected_version": 1
}
```

---

### 2.6 `POST /api/v1/schedule/sessions/{id}/change-venue`
- **Description**: Reassign session venue via `ChangeService` action `schedule.change_venue`.
- **Request Body**:
```json
{
  "new_venue_id": "V02",
  "reason": "Shifted indoors due to weather warning",
  "expected_version": 1
}
```

---

### 2.7 `GET /api/v1/schedule/conflicts`
- **Description**: Detect and list all conflicts across 10 distinct types.
- **Query Parameters**:
  - `severity` (int, optional: 1-4)
  - `status` (string, optional: `OPEN` | `RESOLVED` | `ACCEPTED`)
  - `conflict_type` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "total": 2,
    "items": [
      {
        "id": "cfl_01",
        "conflict_type": "PARTICIPANT_CLASH",
        "severity": 3,
        "status": "OPEN",
        "description": "Participant P0042 is double-booked between E01 Heat M1 (08:00-09:30) and E09 Heat M1 (08:30-10:30)",
        "entity_refs": {
          "participant_id": "P0042",
          "session_a_id": "ses_001",
          "session_b_id": "ses_015"
        },
        "created_at": "2026-10-30T10:00:00Z"
      }
    ]
  },
  "meta": {
    "types_detected": ["PARTICIPANT_CLASH"]
  },
  "warnings": ["Zero venue overlaps does not mean zero conflicts: all 10 types are checked."]
}
```

---

### 2.8 `GET /api/v1/schedule/conflicts/{id}/resolutions`
- **Description**: Candidate venue/time resolutions ranked by conflicts resolved, new conflicts created, and people affected.
- **Response `200 OK`**:
```json
{
  "data": {
    "conflict_id": "cfl_01",
    "recommendations": [
      {
        "action": "schedule.move_session",
        "session_id": "ses_015",
        "suggested_start_at": "2026-10-31T11:00:00Z",
        "suggested_venue_id": "V02",
        "conflicts_resolved": 1,
        "new_conflicts_created": 0,
        "people_affected": 25,
        "rank": 1,
        "rationale": "Moves E09 after E01 teardown and travel buffer"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `POST /api/v1/schedule/conflicts/{id}/apply-resolution`
- **Description**: Execute a selected candidate resolution via `ChangeService`.
- **Request Body**:
```json
{
  "action": "schedule.move_session",
  "payload": {
    "session_id": "ses_015",
    "new_start_at": "2026-10-31T11:00:00Z"
  },
  "reason": "Applied ranked resolution #1"
}
```

---

### 2.10 `GET /api/v1/schedule/unscheduled`
- **Description**: Honest report of scheduled vs unscheduled entrants, failure reasons, and alternatives.
- **Response `200 OK`**:
```json
{
  "data": {
    "total_registrations": 5580,
    "scheduled_count": 4593,
    "unscheduled_count": 987,
    "unplaced_later_round_sessions": 28,
    "reasons_breakdown": {
      "NOT_ON_SITE_LONG_ENOUGH": 412,
      "NO_SLOT_VENUE_FULL_OR_PERSONAL_CLASH": 575
    },
    "comparison_with_prototype": {
      "prototype_unscheduled": 987,
      "current_unscheduled": 987,
      "difference": 0
    },
    "items": [
      {
        "participant_id": "P0012",
        "event_id": "E05",
        "contingent_id": "C02",
        "reason": "NOT_ON_SITE_LONG_ENOUGH",
        "arrival_datetime": "2026-10-31T22:00:00Z",
        "departure_datetime": "2026-10-31T23:30:00Z",
        "alternatives": ["Request participant arrival extension", "Schedule in Late-Arrival Wave L1"]
      }
    ]
  },
  "meta": {},
  "warnings": ["Never silently drop participants: all 987 unscheduled registrations are tracked with explanations."]
}
```

---

### 2.11 `GET /api/v1/schedule/timeline`
- **Description**: Gantt timeline representation by venue for a specified time window.
- **Query Parameters**:
  - `from` (datetime string, optional)
  - `to` (datetime string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "venues": [
      {
        "venue_id": "V01",
        "venue_name": "Main Stage",
        "blocks": [
          {
            "session_id": "ses_001",
            "event_id": "E01",
            "event_name": "Aarohan",
            "round": "prelims",
            "start": "2026-10-31T08:00:00Z",
            "end": "2026-10-31T09:30:00Z",
            "setup_start": "2026-10-31T07:45:00Z",
            "teardown_end": "2026-10-31T09:45:00Z"
          }
        ]
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
