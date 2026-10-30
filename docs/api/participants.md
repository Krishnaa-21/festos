# API Specification: `participants`

> Owner: `P1`  
> Base Path: `/api/v1/participants`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `participants` module provides the single canonical participant record referenced across all FestOS modules (contingents, events, accommodation, checkin, merchandise, transport).
It supports:
- High-performance listing, fuzzy name searching, filtering across contingent, event, diet, accessibility, arrival window, role, and first-class `UNKNOWN` field values.
- Controlled profile CRUD executed strictly through `ChangeService`.
- A resilient lifecycle state machine:
  `EXPECTED` → `ARRIVED` → `CHECKED_IN` → `CHECKED_OUT` (terminal options: `CANCELLED`, `NO_SHOW`, `WITHDRAWN`, `INVALID`, `MERGED`).
- Automated domain event publication (`participant.status_changed`) on `core.bus` upon status transition.
- Comprehensive `Participant 360` operational view aggregating registrations, contingent info, dietary requirements, accessibility needs, merch entitlements, and pluggable section hooks registered via `register_participant_section`.
- Role-based data masking (sensitive contact, medical, accommodation details masked for `VOLUNTEER` roles).
- Audit history timeline tracking every mutation and why-card decision.

---

## 2. Endpoints

### 2.1 `GET /api/v1/participants`
- **Description**: List, filter, and fuzzy search canonical participant records.
- **Query Parameters**:
  - `page` (int, default: 1): Page number.
  - `page_size` (int, default: 20): Items per page (max 100).
  - `sort` (string, default: "name"): Sort field, prefix with `-` for descending (e.g., `-created_at`, `arrival_at`).
  - `q` (string, optional): Fuzzy search on participant name and college.
  - `contingent_id` (string, optional): Filter by contingent ID (e.g., `C05`).
  - `status` (string, optional): Lifecycle status (`EXPECTED`, `ARRIVED`, `CHECKED_IN`, `CHECKED_OUT`, `CANCELLED`, `NO_SHOW`, `WITHDRAWN`, `INVALID`, `MERGED`).
  - `event_id` (string, optional): Filter participants registered for a specific event (e.g., `EV01`).
  - `diet` (string, optional): Filter by dietary need or `UNKNOWN`.
  - `accessibility` (string, optional): Filter by accessibility need presence or specific flag.
  - `unknown_field` (string, optional): Filter records where a specific field is literal `"UNKNOWN"` (e.g., `gender`, `diet`, `accommodation_requested`, `tshirt_size`).
  - `role` (string, optional): Filter by role (`PARTICIPANT`, `LEADER`, `ESCORT`, `JUDGE`, `VOLUNTEER`, `STAFF`).
  - `arrival_window_start` (string ISO, optional): Filter participants arriving on or after datetime.
  - `arrival_window_end` (string ISO, optional): Filter participants arriving on or before datetime.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "P0102",
        "canonical_participant_id": "P0102",
        "source_row_id": "102",
        "contingent_id": "C05",
        "name": "Aarav Sharma",
        "college": "IIT Bombay",
        "email": "a***@iitb.ac.in",
        "phone": "+91 98**** 1234",
        "gender": "Male",
        "diet": "UNKNOWN",
        "housing_preference": "UNKNOWN",
        "accessibility_needs": {},
        "accommodation_requested": "YES",
        "tshirt_size": "L",
        "arrival_at": "2026-10-31T08:30:00Z",
        "departure_at": "2026-11-03T18:00:00Z",
        "age": 20,
        "role": "PARTICIPANT",
        "status": "EXPECTED",
        "version": 1,
        "created_at": "2026-10-30T10:00:00Z",
        "updated_at": "2026-10-30T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "meta": {
    "filter_counts": {
      "total_expected": 2836,
      "with_unknown_fields": 842
    }
  },
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/participants/{id}`
- **Description**: Retrieve a single canonical participant record by ID. Sensitive fields are masked based on caller's role.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "P0102",
    "canonical_participant_id": "P0102",
    "source_row_id": "102",
    "contingent_id": "C05",
    "name": "Aarav Sharma",
    "college": "IIT Bombay",
    "email": "aarav.sharma@iitb.ac.in",
    "phone": "+91 98765 43210",
    "gender": "Male",
    "diet": "UNKNOWN",
    "housing_preference": "UNKNOWN",
    "accessibility_needs": {},
    "accommodation_requested": "YES",
    "tshirt_size": "L",
    "arrival_at": "2026-10-31T08:30:00Z",
    "departure_at": "2026-11-03T18:00:00Z",
    "age": 20,
    "role": "PARTICIPANT",
    "status": "EXPECTED",
    "version": 1,
    "created_at": "2026-10-30T10:00:00Z",
    "updated_at": "2026-10-30T10:00:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/participants/{id}/360`
- **Description**: Comprehensive 360-degree operational view of the participant. Aggregates contingent details, registered events/teams, dietary profile, accessibility needs, merchandise entitlement/claim status, operational timeline, and dynamic sections mounted via `register_participant_section`.
- **Response `200 OK`**:
```json
{
  "data": {
    "participant": {
      "id": "P0102",
      "canonical_participant_id": "P0102",
      "name": "Aarav Sharma",
      "college": "IIT Bombay",
      "email": "aarav.sharma@iitb.ac.in",
      "phone": "+91 98765 43210",
      "role": "PARTICIPANT",
      "status": "EXPECTED",
      "arrival_at": "2026-10-31T08:30:00Z",
      "departure_at": "2026-11-03T18:00:00Z"
    },
    "contingent": {
      "id": "C05",
      "code": "C05",
      "name": "IIT Bombay Contingent",
      "college": "IIT Bombay",
      "leader_name": "Rohan Deshmukh",
      "leader_found": true,
      "escort_name": "Dr. V. K. Raman",
      "escort_found": false
    },
    "registrations": [
      {
        "registration_id": "reg_001",
        "event_id": "EV01",
        "event_name": "RoboWars",
        "team_id": "TM_05",
        "status": "REGISTERED"
      }
    ],
    "diet": {
      "preference": "UNKNOWN",
      "status": "UNVERIFIED",
      "verification_history": []
    },
    "accessibility": {
      "needs": {},
      "requires_ground_floor": false,
      "requires_accessible_transit": false
    },
    "merchandise": {
      "tshirt_size": "L",
      "entitlement": "PENDING",
      "claims": []
    },
    "operational_status": {
      "current_status": "EXPECTED",
      "can_transition_to": ["ARRIVED", "CANCELLED", "NO_SHOW"],
      "last_updated": "2026-10-30T10:00:00Z"
    },
    "sections": {
      "accommodation": {
        "status": "UNASSIGNED",
        "plan_kind": null,
        "room": null
      },
      "transport": {
        "shuttle_assigned": false
      }
    }
  },
  "meta": {
    "masked_fields": []
  },
  "warnings": [
    "Dietary preference is UNKNOWN - flag for desk verification on arrival."
  ]
}
```

---

### 2.4 `POST /api/v1/participants`
- **Description**: Register a new participant via `ChangeService` (`participant.create`).
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": null,
  "reason": "Late manual registration approved by Festival Director",
  "dry_run": false,
  "payload": {
    "contingent_id": "C05",
    "name": "Priya Nair",
    "college": "IIT Bombay",
    "email": "priya.nair@iitb.ac.in",
    "phone": "+91 99887 76655",
    "gender": "Female",
    "diet": "VEG",
    "accommodation_requested": "YES",
    "tshirt_size": "M",
    "arrival_at": "2026-10-31T09:00:00Z",
    "departure_at": "2026-11-03T18:00:00Z"
  }
}
```
- **Response `200 OK`**: Standard Envelope containing `ChangeResult`.

---

### 2.5 `PATCH /api/v1/participants/{id}`
- **Description**: Update participant profile fields via `ChangeService` (`participant.update`).
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Update dietary preference confirmed by contingent leader",
  "dry_run": false,
  "payload": {
    "diet": "VEG",
    "tshirt_size": "XL"
  }
}
```
- **Response `200 OK`**: Standard Envelope containing `ChangeResult`.

---

### 2.6 `POST /api/v1/participants/{id}/status`
- **Description**: Transition participant lifecycle status via `ChangeService` (`participant.change_status`). Automatically publishes `participant.status_changed` on `core.bus`.
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Physical arrival verified at reception desk",
  "dry_run": false,
  "payload": {
    "status": "ARRIVED"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_9a8b7c6d",
    "status": "APPLIED",
    "violations": [],
    "audit_event_ids": ["aud_112233"],
    "impact": {
      "previous_status": "EXPECTED",
      "new_status": "ARRIVED",
      "bus_event_published": "participant.status_changed"
    },
    "recommendations": [],
    "warnings": []
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/participants/{id}/timeline`
- **Description**: Retrieve chronological audit events and state change history for this participant.
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0102",
    "events": [
      {
        "id": "aud_112233",
        "action": "participant.change_status",
        "actor_id": "usr_reception01",
        "actor_role": "VOLUNTEER",
        "reason": "Physical arrival verified at reception desk",
        "timestamp": "2026-10-31T08:35:10Z",
        "before": {"status": "EXPECTED"},
        "after": {"status": "ARRIVED"}
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
