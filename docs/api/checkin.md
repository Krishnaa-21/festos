# API Specification: `checkin`

> Owner: `@P2` (shared with `@P3` for UI)  
> Base Path: `/api/v1/checkin`  
> Status: `APPROVED`

---

## 1. Overview
The Check-in module handles operational reception desk workflows, barcode/QR rapid scanning, one-handed mobile and tablet layouts, real-time room readiness alerts, dietary & accessibility warnings, instant UNKNOWN field verification prompts, arrival boards, check-out cleaning triggers, event-driven cancellation/no-show bed releases, and an offline operation sync engine.

All check-ins are idempotent using `client_op_id`. If a participant's assigned room is still in `CLEANING`, check-in is blocked and alternative ready rooms are suggested. Offline desks can buffer check-in and check-out actions locally and replay them via `POST /api/v1/checkin/sync`, where server state wins and conflicts are returned with detailed diagnostics.

---

## 2. Endpoints

### 2.1 `GET /api/v1/checkin/board`
- **Description**: Real-time arrival board tracking pending arrivals, arrived at desk, checked-in, and late arrivals.
- **Permissions**: `checkin:read`
- **Response `200 OK`**:
```json
{
  "data": {
    "counts": {
      "pending_count": 2180,
      "arrived_count": 42,
      "checked_in_count": 594,
      "late_arrivals_count": 18
    },
    "late_arrivals": [
      {
        "participant_id": "P0412",
        "name": "Aditya Verma",
        "college": "BITS Pilani",
        "contingent_id": "C08",
        "flight_pnr": "6E-204",
        "expected_arrival": "2026-10-30T18:00:00Z",
        "delay_minutes": 150,
        "is_curfew_breach": true,
        "notes": "Late night arrival past 22:00 campus gate curfew"
      }
    ],
    "recent_checkins": [
      {
        "participant_id": "P0102",
        "name": "Aarav Sharma",
        "college": "IIT Bombay",
        "room_number": "H3-101",
        "checked_in_at": "2026-10-30T10:15:00Z",
        "volunteer": "Dr. Devashish Roy"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/checkin/search?q={query}`
- **Description**: Rapid search by participant ID, name, email, contingent code, or barcode/QR string.
- **Permissions**: `checkin:read`
- **Query Parameters**:
  - `q`: Search string (e.g., `P0102`, `Aarav`, `C05`)
- **Response `200 OK`**:
```json
{
  "data": [
    {
      "id": "P0102",
      "name": "Aarav Sharma",
      "contingent_id": "C05",
      "college": "IIT Bombay",
      "role": "LEADER",
      "status": "EXPECTED",
      "assigned_bed": "rm_B1_0_01_bed1",
      "room_status": "READY"
    }
  ],
  "meta": { "total": 1 },
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/checkin/participant/{id}`
- **Description**: Rapid search and scan participant lookup with room readiness, accessibility, diet alerts, and UNKNOWN field prompts.
- **Permissions**: `checkin:read`
- **Response `200 OK`**:
```json
{
  "data": {
    "participant": {
      "id": "P0102",
      "name": "Aarav Sharma",
      "contingent_id": "C05",
      "college": "IIT Bombay",
      "role": "LEADER",
      "status": "EXPECTED",
      "gender": "Male",
      "age": 21,
      "is_minor": false,
      "diet": "UNKNOWN",
      "accommodation_requested": "YES"
    },
    "room_assignment": {
      "bed_id": "B1-0-01-A",
      "room_id": "B1-0-01",
      "room_number": "001",
      "building": "Hostel B1",
      "floor": 0,
      "cleaning_status": "READY",
      "cleaning_ready_at": "2026-10-30T09:00:00Z",
      "is_accessible": true
    },
    "alerts": {
      "accessibility": "Requires Ground Floor Bed (Wheelchair ramp verified)",
      "diet": "Diet is UNKNOWN (Prompt for quick verification at desk)",
      "safety": null
    },
    "unknown_prompts": [
      {
        "field": "diet",
        "prompt": "Select dietary category for meal token provisioning",
        "options": ["VEG", "NON_VEG", "JAIN"]
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/checkin/checkin` (or `/verify-arrival`)
- **Description**: Idempotent participant check-in. Verifies stay assignment, blocks check-in if assigned room is not ready (`cleaning_status != READY` or active cleaning buffer), and offers alternative ready rooms.
- **Permissions**: `checkin:write`
- **Headers**:
  - `Idempotency-Key` (UUID, optional if `client_op_id` in body)
- **Request Body**:
```json
{
  "client_op_id": "op_987654321",
  "participant_id": "P0102",
  "wristband_code": "WB_987654",
  "verified_fields": {
    "diet": "VEG"
  },
  "desk_operator": "Volunteer Lead",
  "override_room_id": null
}
```
- **Response `200 OK` (Room Ready)**:
```json
{
  "data": {
    "participant_id": "P0102",
    "status": "CHECKED_IN",
    "checked_in_at": "2026-10-30T10:15:00Z",
    "bed_id": "B1-0-01-A",
    "room_number": "B1-0-01",
    "room_key_released": true,
    "merch_eligible": true
  },
  "meta": { "client_op_id": "op_987654321" },
  "warnings": []
}
```
- **Response `422 CONSTRAINT_VIOLATION` (Room In Cleaning / Not Ready)**:
```json
{
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Assigned room 'B1-0-01' is not READY (Status: CLEANING until 2026-10-30T12:00:00Z).",
    "details": {
      "assigned_room_id": "B1-0-01",
      "cleaning_status": "CLEANING",
      "cleaning_ready_at": "2026-10-30T12:00:00Z",
      "alternative_rooms": [
        {
          "room_id": "B1-0-02",
          "block": "B1",
          "floor": 0,
          "capacity": 3,
          "available_beds": 2,
          "accessible": true,
          "gender_class": "boys"
        }
      ]
    }
  }
}
```

---

### 2.5 `POST /api/v1/checkin/checkout`
- **Description**: Check out participant, free bed, mark stay `COMPLETED`, and transition room to `CLEANING` status with cleaning countdown timer based on `cleaning_buffer_minutes`.
- **Permissions**: `checkin:write`
- **Request Body**:
```json
{
  "client_op_id": "op_checkout_001",
  "participant_id": "P0102",
  "bed_id": "B1-0-01-A",
  "checkout_notes": "Departing on flight 6E-481"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0102",
    "status": "CHECKED_OUT",
    "bed_id": "B1-0-01-A",
    "room_id": "B1-0-01",
    "room_status": "CLEANING",
    "cleaning_buffer_minutes": 180,
    "cleaning_ready_at": "2026-10-30T13:15:00Z"
  },
  "meta": { "client_op_id": "op_checkout_001" },
  "warnings": []
}
```

---

### 2.6 `PATCH /api/v1/checkin/participant/{id}/arrival`
- **Description**: Record early or late arrival time updates, recalculating delay minutes and curfew breach flags.
- **Permissions**: `checkin:write`
- **Request Body**:
```json
{
  "updated_arrival_at": "2026-10-30T23:30:00Z",
  "delay_reason": "Flight rescheduled due to weather",
  "transport_mode": "Flight 6E-204"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0412",
    "arrival_at": "2026-10-30T23:30:00Z",
    "is_curfew_breach": true,
    "warning": "Arrival past 22:00 campus curfew: requires gate coordination."
  },
  "meta": {},
  "warnings": ["Late night arrival past curfew window (22:00)."]
}
```

---

### 2.7 `POST /api/v1/checkin/sync` (Batch Offline Sync)
- **Description**: Synchronize buffered offline desk operations. Evaluates idempotency via `client_op_id`, applies valid ops, detects conflicts against current server state, and explains conflict reasons.
- **Permissions**: `checkin:write`
- **Request Body**:
```json
{
  "device_id": "desk_terminal_03",
  "sync_batch_id": "batch_20261030_0900",
  "operations": [
    {
      "client_op_id": "op_1001",
      "op_type": "CHECKIN",
      "participant_id": "P0102",
      "timestamp": "2026-10-30T08:30:00Z",
      "payload": {
        "wristband_code": "WB_987654",
        "verified_fields": { "diet": "VEG" }
      }
    },
    {
      "client_op_id": "op_1002",
      "op_type": "CHECKOUT",
      "participant_id": "P0055",
      "timestamp": "2026-10-30T08:35:00Z",
      "payload": {
        "bed_id": "B2-1-04-B"
      }
    }
  ]
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "batch_id": "batch_20261030_0900",
    "processed_count": 2,
    "applied_count": 1,
    "duplicate_count": 1,
    "conflict_count": 0,
    "results": [
      {
        "client_op_id": "op_1001",
        "status": "APPLIED",
        "message": "Participant P0102 successfully checked in."
      },
      {
        "client_op_id": "op_1002",
        "status": "DUPLICATE_IGNORED",
        "message": "Operation op_1002 already processed previously."
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
Possible operation statuses:
- `APPLIED`: Operation successfully applied to server state.
- `DUPLICATE_IGNORED`: Operation already applied previously with same `client_op_id`.
- `CONFLICT`: Server state incompatible (e.g., bed reallocated, participant already cancelled, room in maintenance). Reason explained in `message`.

---

### 2.8 `GET /api/v1/checkin/reallocations/suggestions`
- **Description**: Retrieve bed reallocation suggestions generated when beds are freed by participant cancellations or no-shows. These are recommendations and are NEVER auto-applied without organizer confirmation.
- **Permissions**: `checkin:read`
- **Response `200 OK`**:
```json
{
  "data": {
    "suggestions": [
      {
        "suggestion_id": "sug_01",
        "freed_bed_key": "B1-0-01-A",
        "freed_room_id": "B1-0-01",
        "freed_by_participant_id": "P0103",
        "reason": "PARTICIPANT_CANCELLED",
        "suggested_participant_id": "P0104",
        "suggested_participant_name": "Sneha Mukherjee",
        "contingent_id": "C05",
        "priority_score": 92.5,
        "cohesion_benefit": "Unifies IIT Bombay participant with 12 contingent members in Hostel B1.",
        "created_at": "2026-10-30T09:15:00Z"
      }
    ]
  },
  "meta": { "count": 1 },
  "warnings": ["Suggestions are advisory only. FestOS never auto-applies reallocation without organizer sign-off."]
}
```

---

## 3. Event Subscriptions

- **Topic**: `participant.status_changed`
  - When status transitions to `CANCELLED` or `NO_SHOW`:
    1. Active stay assignments for the participant are released (status set to `CANCELLED`).
    2. A reallocation suggestion is generated for eligible unplaced participants matching the room gender, accessibility, and contingent affinity.
    3. The suggestion is persisted to the suggestions table for manual operator review.
