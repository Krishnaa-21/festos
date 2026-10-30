# API Specification: `contingents`

> Owner: `P1`  
> Base Path: `/api/v1/contingents`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `contingents` module provides operational coordination and tracking across the 38 institutional contingents participating in Aarohan (EPINOIA 2026).
Key capabilities:
- Comprehensive profiles for all 38 contingents including declared strength vs actual canonical participant count.
- Leader and escort matching against canonical participant records (`FOUND` vs `MISSING`).
- Arrival and departure coordination across members to plan reception and transport waves.
- Real-time attendance, event participation breakdowns, dietary requirements, and merchandise distribution status.
- Group alerts flagging size discrepancies, missing escorts, and travel window anomalies.
- Fragmentation analysis and leader proximity metrics (querying `accommodation.public` when present, or gracefully degrading with clear warnings).

---

## 2. Endpoints

### 2.1 `GET /api/v1/contingents`
- **Description**: List all 38 contingents with basic metrics (declared strength, actual strength, mismatch gap, leader, escort).
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
  - `q` (string, optional): Search by college name or contingent code (e.g., `C05`).
  - `has_mismatch` (boolean, optional): Filter only contingents where `strength_declared != actual_strength`.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "C05",
        "code": "C05",
        "name": "IIT Bombay Contingent",
        "college": "IIT Bombay",
        "leader": "Rohan Deshmukh",
        "escort": "Dr. V. K. Raman",
        "strength_declared": 80,
        "strength_actual": 72,
        "gap": -8,
        "leader_status": "FOUND",
        "escort_status": "MISSING",
        "status": "ACTIVE"
      }
    ],
    "total": 38,
    "page": 1,
    "page_size": 50,
    "total_pages": 1
  },
  "meta": {
    "total_declared": 2842,
    "total_actual": 2836,
    "contingents_with_mismatch": 7
  },
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/contingents/{id}`
- **Description**: Get single contingent profile details.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "C05",
    "code": "C05",
    "name": "IIT Bombay Contingent",
    "college": "IIT Bombay",
    "leader": "Rohan Deshmukh",
    "escort": "Dr. V. K. Raman",
    "strength_declared": 80,
    "strength_actual": 72,
    "preferences": "Male/Female separate blocks requested; ground floor for 2 participants",
    "contact_name": "Rohan Deshmukh",
    "contact_phone": "+91 98765 00001",
    "contact_email": "contingent.c05@iitb.ac.in",
    "status": "ACTIVE",
    "version": 1,
    "created_at": "2026-10-30T10:00:00Z",
    "updated_at": "2026-10-30T10:00:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/contingents/{id}/status`
- **Description**: Detailed operational status of the contingent covering arrival distribution, member attendance, leader/escort participant linkage, event participation, dietary breakdown, merchandise distribution, and housing fragmentation.
- **Response `200 OK`**:
```json
{
  "data": {
    "contingent_id": "C05",
    "college": "IIT Bombay",
    "strength": {
      "declared": 80,
      "actual": 72,
      "gap": -8,
      "status": "DISCREPANCY_UNDER"
    },
    "leadership": {
      "leader": {
        "name": "Rohan Deshmukh",
        "participant_id": "P0102",
        "status": "FOUND",
        "role": "LEADER",
        "attendance": "EXPECTED"
      },
      "escort": {
        "name": "Dr. V. K. Raman",
        "participant_id": null,
        "status": "MISSING",
        "note": "Escort is declared in contingent master but missing from participant rosters"
      }
    },
    "attendance": {
      "EXPECTED": 68,
      "ARRIVED": 4,
      "CHECKED_IN": 0,
      "CHECKED_OUT": 0,
      "CANCELLED": 0,
      "NO_SHOW": 0,
      "WITHDRAWN": 0,
      "INVALID": 0,
      "MERGED": 0
    },
    "travel_coordination": {
      "earliest_arrival": "2026-10-31T06:00:00Z",
      "latest_departure": "2026-11-03T20:00:00Z",
      "arrival_windows": [
        {"window": "2026-10-31 Morning (06:00-12:00)", "count": 52},
        {"window": "2026-10-31 Afternoon (12:00-18:00)", "count": 20}
      ]
    },
    "event_participation": {
      "total_registrations": 142,
      "unique_events": 16,
      "events": [
        {"event_id": "EV01", "name": "RoboWars", "participants_count": 8},
        {"event_id": "EV05", "name": "Hackathon", "participants_count": 12}
      ]
    },
    "dietary_summary": {
      "VEG": 45,
      "NON_VEG": 18,
      "JAIN": 2,
      "UNKNOWN": 7
    },
    "merchandise_summary": {
      "eligible": 72,
      "claimed": 0,
      "pending": 72,
      "size_breakdown": {
        "S": 10,
        "M": 28,
        "L": 24,
        "XL": 8,
        "UNKNOWN": 2
      }
    },
    "alerts": [
      {
        "code": "STRENGTH_MISMATCH",
        "severity": 2,
        "message": "Declared strength 80 differs from actual rosters 72 (gap: -8)."
      },
      {
        "code": "ESCORT_MISSING",
        "severity": 3,
        "message": "Escort Dr. V. K. Raman not found in participant roster."
      }
    ],
    "housing_fragmentation": {
      "status": "UNAVAILABLE",
      "properties_count": 0,
      "buildings_count": 0,
      "leader_proximity_meters": null,
      "warning": "Accommodation plan not yet live or accommodation.public unavailable"
    }
  },
  "meta": {},
  "warnings": [
    "Declared strength (80) does not match roster count (72)"
  ]
}
```

---

### 2.4 `PATCH /api/v1/contingents/{id}`
- **Description**: Update contingent information via `ChangeService` (`contingent.update`).
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Update contact information for contingent leader",
  "dry_run": false,
  "payload": {
    "contact_phone": "+91 98765 99999",
    "preferences": "Require accommodation in block C if possible"
  }
}
```
- **Response `200 OK`**: Standard Envelope containing `ChangeResult`.
