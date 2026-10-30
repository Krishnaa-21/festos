# API Specification: Events & Competitions

> Owner: `P1`  
> Base Path: `/api/v1/events`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Events module manages event profiles, requirements, solo vs team classifications, rounds, participant registrations, provisional team reconciliation, and judge registration with conflict detection. All mutating operations flow through `ChangeService`.

---

## 2. Endpoints

### 2.1 `GET /api/v1/events`
- **Description**: List all events with metadata, rounds, and requirements.
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
  - `solo_team` (string, optional: `solo` | `team`)
  - `q` (string, optional: search by name or ID)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "E01",
        "name": "Aarohan",
        "solo_team": "SOLO",
        "rounds": 3,
        "rounds_text": "prelims|semis|finals",
        "duration_min": 90,
        "venue_requirements": "audio; seating",
        "equipment_needs": "barricades; tables",
        "volunteers_needed": 10,
        "judges_needed": 2,
        "registrations_count": 180,
        "status": "ACTIVE"
      }
    ],
    "total": 31,
    "page": 1,
    "page_size": 50,
    "total_pages": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/events/{id}`
- **Description**: Detailed profile of an event including requirements, judge slots, and registered participants.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "E03",
    "name": "Case Clash",
    "solo_team": "TEAM",
    "rounds": 3,
    "rounds_text": "prelims|semis|finals",
    "duration_min": 120,
    "venue_requirements": "power; tables",
    "equipment_needs": "projector; 2 extension cords",
    "volunteers_needed": 10,
    "judges_needed": 3,
    "min_team_size": 2,
    "max_team_size": 5,
    "provisional_teams_count": 32,
    "status": "ACTIVE",
    "version": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/events/{id}/registrations`
- **Description**: Registrations for this event with team and provisional team details.
- **Response `200 OK`**:
```json
{
  "data": {
    "event_id": "E03",
    "registrations": [
      {
        "registration_id": "REG_1234",
        "participant_id": "P0042",
        "participant_name": "Aarav Sharma",
        "contingent_id": "C05",
        "team_id": null,
        "provisional_team_id": "TEAM_C05_E03",
        "team_label": "ASSUMED"
      }
    ],
    "total": 120
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/events`
- **Description**: Create a new event via `ChangeService` action `event.create`.
- **Headers**: `Idempotency-Key` (UUID)

---

### 2.5 `PUT /api/v1/events/{id}`
- **Description**: Update event details via `ChangeService` action `event.update`.
- **Headers**: `Idempotency-Key` (UUID)

---

### 2.6 `POST /api/v1/events/{id}/cancel`
- **Description**: Cancel an event via `ChangeService` action `event.cancel`. Cascades to cancel scheduled sessions.
- **Request Body**:
```json
{
  "reason": "Host college pullout",
  "expected_version": 1
}
```

---

### 2.7 `POST /api/v1/events/{id}/merge`
- **Description**: Merge two events via `ChangeService` action `event.merge`.
- **Request Body**:
```json
{
  "target_event_id": "E02",
  "reason": "Combined prelims",
  "expected_version": 1
}
```

---

### 2.8 `POST /api/v1/events/{id}/extend-duration`
- **Description**: Extend event duration via `ChangeService` action `event.extend_duration`. Triggers conflict detector.
- **Request Body**:
```json
{
  "new_duration_min": 150,
  "reason": "Extra presentation time for finals",
  "expected_version": 1
}
```

---

### 2.9 `GET /api/v1/events/teams/provisional`
- **Description**: Report team reconciliation stats and list provisional teams derived from contingent + event.
- **Response `200 OK`**:
```json
{
  "data": {
    "total_team_registrations": 1810,
    "missing_team_id_count": 1810,
    "provisional_teams_count": 312,
    "label": "ASSUMED",
    "provisional_teams": [
      {
        "provisional_team_id": "TEAM_C01_E03",
        "contingent_id": "C01",
        "event_id": "E03",
        "member_count": 4,
        "participant_ids": ["P0001", "P0002", "P0003", "P0004"],
        "status": "ASSUMED"
      }
    ]
  },
  "meta": {},
  "warnings": ["1,810 team registrations lack team IDs in source data. Provisional groupings are ASSUMED and editable."]
}
```

---

### 2.10 `GET /api/v1/events/judges`
- **Description**: List registered judges, unassigned judge slots across scheduled sessions, and conflict flags.
- **Response `200 OK`**:
```json
{
  "data": {
    "judges": [
      {
        "id": "JDG_01",
        "name": "Prof. Rao",
        "college_affiliation": "C05",
        "is_participant": false,
        "is_college_conflict": true,
        "assigned_sessions": ["ses_123"]
      }
    ],
    "unassigned_slots_count": 48,
    "unassigned_slots": [
      {
        "session_id": "ses_456",
        "event_id": "E01",
        "round": "finals",
        "slot_number": 1,
        "status": "UNASSIGNED"
      }
    ]
  },
  "meta": {},
  "warnings": ["Source pack provides zero judge data. Judge registry relies on manual entry; all unfilled slots are shown as UNASSIGNED gaps."]
}
```

---

### 2.11 `POST /api/v1/events/judges`
- **Description**: Manually register a judge and check for college / competitor conflicts.
- **Request Body**:
```json
{
  "name": "Dr. Sunita Sen",
  "email": "sunita@example.com",
  "college_affiliation": "C12",
  "expert_events": ["E01", "E05"]
}
```
