# API Specification: `staff`

> Owner: `P1`  
> Base Path: `/api/v1/staff`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Staff and Volunteer Management** module governs the deployment of all 48 core team members and festival volunteers.
It coordinates:
- Staff profiles, roles, skills, availability, and default shift schedules (seeded from `core_team.csv`).
- Shift assignments to event sessions, venues, and registration/merchandise desks.
- Handover notes enforcement: any shift modification or staff replacement without a handover note is flagged (`HANDOVER_NOTE_MISSING`).
- Volunteer demand vs. on-shift supply computation over time based on scheduled event sessions (`volunteers_required`).
- Detection of the maximum staffing gap and uncovered slots (baseline peak requirement: 74 vs 18 on shift, ~34 hours of gap).
- Understaffed event alerts and overloaded staff alerts (daily hours exceeding threshold, consecutive hours without break).
- Shift-overlap and double-venue assignment detection including venue travel times.
- Emergency replacement ranking engine: scores candidates based on availability window, nearest venue travel time, skill match, and non-overloaded status.
- Conflict of interest detection: flags core team members registered as competitors, or acting as judges/escorts for their own contingents.
- ChangeService operations: `staff.assign`, `staff.replace`.

---

## 2. Endpoints

### 2.1 `GET /api/v1/staff`
- **Description**: List staff profiles with roles, shift bands, skills, and status.
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
  - `role` (string, optional: e.g. `Registration Desk`, `Hospitality`, `Events Team`, `Logistics Head`, `Merchandise Desk`, `Food Coordinator`, `Volunteer`, `Festival Director`)
  - `shift` (string, optional: `06:00-14:00`, `14:00-22:00`, `22:00-06:00`, `10:00-18:00`)
  - `skill` (string, optional)
  - `q` (string, optional: search by name or member ID)
- **Response `200 OK`**:
```json
{
  "data": {
    "staff": [
      {
        "id": "ST01",
        "name": "Aditi Verma",
        "role": "Registration Desk",
        "shift": "22:00-06:00",
        "phone": "+91-8751107695",
        "skills": ["registration", "first_aid", "crowd_management"],
        "status": "ACTIVE",
        "hours_scheduled_today": 8.0,
        "is_participant": false,
        "conflict_flags": []
      }
    ],
    "total": 48,
    "page": 1,
    "page_size": 50
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/staff/{id}`
- **Description**: Returns detailed staff member profile, active assignments, and workload metrics.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "ST01",
    "name": "Aditi Verma",
    "role": "Registration Desk",
    "shift": "22:00-06:00",
    "phone": "+91-8751107695",
    "skills": ["registration", "first_aid", "crowd_management"],
    "status": "ACTIVE",
    "active_shifts": [
      {
        "id": "shf_001",
        "session_id": "ses_e01_r1",
        "venue_id": "V01",
        "role_required": "Registration Desk",
        "start_at": "2026-10-31T06:00:00Z",
        "end_at": "2026-10-31T14:00:00Z",
        "status": "SCHEDULED",
        "handover_notes": "Morning check-in desk lead"
      }
    ],
    "workload": {
      "total_hours": 8.0,
      "consecutive_hours": 8.0,
      "is_overloaded": false
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/staff/shifts`
- **Description**: List scheduled shifts and venue assignments.
- **Query Parameters**:
  - `staff_id` (string, optional)
  - `session_id` (string, optional)
  - `venue_id` (string, optional)
  - `date` (string, optional: YYYY-MM-DD)
  - `status` (string, optional: `SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`)
- **Response `200 OK`**:
```json
{
  "data": {
    "shifts": [
      {
        "id": "shf_001",
        "staff_id": "ST01",
        "staff_name": "Aditi Verma",
        "role_required": "Registration Desk",
        "location": "Auditorium",
        "session_id": "ses_e01_r1",
        "start_at": "2026-10-31T06:00:00Z",
        "end_at": "2026-10-31T14:00:00Z",
        "handover_notes": "Morning desk lead",
        "status": "SCHEDULED"
      }
    ],
    "total": 144
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/staff/shifts/assign`
- **Description**: Assign a staff member to a shift or session via ChangeService (`staff.assign`).
- **Request Body**:
```json
{
  "payload": {
    "staff_id": "ST07",
    "session_id": "ses_e03_r1",
    "venue_id": "V02",
    "role_required": "Volunteer",
    "start_at": "2026-10-31T10:00:00Z",
    "end_at": "2026-10-31T13:00:00Z",
    "handover_notes": "Assist judge scoring table"
  },
  "reason": "Cover volunteer requirement for Coding Prelims",
  "dry_run": false
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_staff_assign_01",
    "status": "APPLIED",
    "data": {
      "shift_id": "shf_new_01",
      "staff_id": "ST07",
      "session_id": "ses_e03_r1"
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/staff/shifts/{id}/replace`
- **Description**: Emergency replacement of an assigned staff member via ChangeService (`staff.replace`).
- **Request Body**:
```json
{
  "payload": {
    "replacement_staff_id": "ST15",
    "handover_notes": "Handing over stage audio cable kit to Tanvi Sharma"
  },
  "reason": "Original staff member unwell; emergency substitution",
  "dry_run": false
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_replace_01",
    "status": "APPLIED",
    "data": {
      "shift_id": "shf_001",
      "previous_staff_id": "ST01",
      "replacement_staff_id": "ST15",
      "handover_notes": "Handing over stage audio cable kit to Tanvi Sharma"
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/staff/demand`
- **Description**: Calculates volunteer requirement demand over time from scheduled event sessions, compares against core team on shift, and reports uncovered gaps.
- **Response `200 OK`**:
```json
{
  "data": {
    "peak_requirement": 74,
    "peak_available_on_shift": 18,
    "max_gap": 56,
    "uncovered_hours_total": 34.0,
    "demand_timeline": [
      {
        "time_window_start": "2026-10-31T10:00:00Z",
        "time_window_end": "2026-10-31T11:00:00Z",
        "volunteers_required": 74,
        "staff_on_shift": 18,
        "gap": 56,
        "is_understaffed": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/staff/overloaded`
- **Description**: Returns list of staff members exceeding daily maximum hours (10h) or consecutive working hours (8h) without a mandatory rest window.
- **Response `200 OK`**:
```json
{
  "data": {
    "overloaded_staff": [
      {
        "staff_id": "ST03",
        "name": "Arjun Singh",
        "scheduled_hours": 12.0,
        "consecutive_hours": 10.0,
        "threshold_hours": 10.0,
        "reason": "Exceeds daily maximum 10-hour limit"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `GET /api/v1/staff/conflicts`
- **Description**: Surfaces staff members with conflicts of interest:
  - Core team member who is also registered as an active competitor in `participant`.
  - Staff member acting as judge or contingent escort for their own contingent.
  - Overlapping shifts across different venues with travel time infeasibility.
- **Response `200 OK`**:
```json
{
  "data": {
    "conflicts": [
      {
        "staff_id": "ST11",
        "name": "Riya Das",
        "conflict_type": "PARTICIPANT_STAFF_DUAL_ROLE",
        "details": "Core team member is also registered as competitor in solo dance event"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `GET /api/v1/staff/replacements/suggest`
- **Description**: Evaluates and suggests ranked emergency replacement candidates for a specific session/shift window.
- **Query Parameters**:
  - `shift_id` (string, optional)
  - `venue_id` (string, required)
  - `start_at` (ISO datetime, required)
  - `end_at` (ISO datetime, required)
  - `role_required` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "suggestions": [
      {
        "staff_id": "ST15",
        "name": "Tanvi Sharma",
        "role": "Volunteer",
        "travel_time_min": 15,
        "skills_match": true,
        "current_hours": 4.0,
        "is_available": true,
        "score": 92.5
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.10 `GET /api/v1/staff/reports/staff-coverage`
- **Description**: Generates downloadable CSV report for staff coverage and hourly gap analysis.
- **Response**: `text/csv; filename=staff_coverage.csv`
