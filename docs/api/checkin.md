# API Specification: `checkin`

> Owner: `@P2` (shared with `@P3` for UI)  
> Base Path: `/api/v1/checkin`  
> Status: `REVIEW`

---

## 1. Overview
The Check-in module handles operational reception desk workflows, barcode/QR rapid scanning, one-handed mobile and tablet layouts, real-time room readiness alerts, dietary & accessibility warnings, instant UNKNOWN field verification prompts, arrival boards, and check-out cleaning triggers.

---

## 2. Endpoints

### 2.1 `GET /api/v1/checkin/board`
- **Description**: Real-time arrival board tracking pending arrivals, arrived at desk, checked-in, and late arrivals.
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

### 2.2 `GET /api/v1/checkin/participant/{id}`
- **Description**: Rapid search and scan participant lookup with room readiness, accessibility, diet alerts, and UNKNOWN field prompts.
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
      "bed_id": "H3-101-A",
      "room_number": "101",
      "building": "Hostel 3 (Wing B)",
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

### 2.3 `POST /api/v1/checkin/verify-arrival`
- **Description**: Verify arrival, apply wristband, and transition status to CHECKED_IN.
- **Headers**:
  - `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "participant_id": "P0102",
  "wristband_code": "WB_987654",
  "verified_fields": {
    "diet": "VEG"
  },
  "desk_operator": "Volunteer Lead"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0102",
    "status": "CHECKED_IN",
    "checked_in_at": "2026-10-30T10:15:00Z",
    "room_key_released": true,
    "merch_eligible": true
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/checkin/checkout`
- **Description**: Check out participant, free bed, and transition room to CLEANING status with 180m countdown buffer.
- **Headers**:
  - `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "participant_id": "P0102",
  "bed_id": "H3-101-A",
  "checkout_notes": "Departing on flight 6E-481"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0102",
    "status": "CHECKED_OUT",
    "bed_id": "H3-101-A",
    "room_status": "CLEANING",
    "cleaning_buffer_minutes": 180,
    "estimated_ready_at": "2026-10-30T13:15:00Z"
  },
  "meta": {},
  "warnings": []
}
```
