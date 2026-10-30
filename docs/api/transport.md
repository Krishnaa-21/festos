# API Specification: `transport`

> Owner: `P1`  
> Base Path: `/api/v1/transport`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Duty-of-Care and Shuttle Planner** module ensures that participants travelling to/from external accommodation properties, late-night arrivals/departures, and minors housed off-campus are provided safe, verified transportation and supervision.

Key principles:
- **Assumed Parameters**: As no raw transportation dataset exists in the festival data pack, all transport parameters (`shuttle_capacity_seats`, `shuttle_vehicle_count`, `shuttle_travel_min`, `transport_hours`, `late_night_window`, `escort_availability`) originate from configurable assumptions and are clearly labelled as `ASSUMED`.
- **Shuttle Planning**: Identifies participants assigned to external stays (from accommodation properties), groups journeys by property and time window (arrivals, departures, events), and computes:
  $$\text{required\_runs} = \left\lceil \frac{\text{passengers}}{\text{capacity}} \right\rceil$$
  It compares required runs with available fleet capacity/operating hours to flag transport deficits.
- **Accommodation Integration**: Exposes `transport_feasible(property_id, time)` to validate external stay assignments (rule 6 of the accommodation engine).
- **Night-Safety Roster**: Identifies late-night arrivals/departures (in assumed window, e.g. 22:00–06:00) and unverified movements, assigning dedicated escorts/volunteers.
- **Guardian Approval Queue**: Dedicated approval flow for minors (<18 years old) residing in external accommodation properties (~71 minors identified in baseline analysis).
- **Plain-Text Safety Alerts**: Actionable text notifications (e.g. `"14 participants scheduled to leave Lakeview Hotel at 00:30 with no verified shuttle"`).
- **Safety Coverage Dashboard**: High-level summary of total passengers, confirmed capacity, uncovered requests, late-night movements, minor approvals, unassigned escorts, and property risk ratings.
- **Participant 360 Integration**: Registers the dynamic `'transport'` section detailing a participant's assigned shuttles, departure times, escort details, and minor approval status.

---

## 2. Endpoints

### 2.1 `GET /api/v1/transport/assumptions`
- **Description**: Returns all configurable transport planning assumptions and operational hours.
- **Response `200 OK`**:
```json
{
  "data": {
    "assumptions": {
      "shuttle_capacity_seats": { "value": 15, "is_assumed": true, "source": "ASSUMED" },
      "shuttle_vehicle_count": { "value": 4, "is_assumed": true, "source": "ASSUMED" },
      "shuttle_travel_min": { "value": 25, "is_assumed": true, "source": "ASSUMED" },
      "transport_hours_start": { "value": "06:00", "is_assumed": true, "source": "ASSUMED" },
      "transport_hours_end": { "value": "24:00", "is_assumed": true, "source": "ASSUMED" },
      "late_night_start": { "value": "22:00", "is_assumed": true, "source": "ASSUMED" },
      "late_night_end": { "value": "06:00", "is_assumed": true, "source": "ASSUMED" },
      "escort_availability_count": { "value": 12, "is_assumed": true, "source": "ASSUMED" }
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `PATCH /api/v1/transport/assumptions`
- **Description**: Updates one or more transport planning assumptions via ChangeService (`transport.update_assumptions`). Automatically recalculates the shuttle plan.
- **Request Body**:
```json
{
  "payload": {
    "shuttle_capacity_seats": 20,
    "shuttle_vehicle_count": 6
  },
  "reason": "Contracted 2 additional mini-buses for external property transfer"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_assump_trf_01",
    "status": "APPLIED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/transport/shuttles/plan`
- **Description**: Computes required shuttle runs per property and time window, comparing passenger demand against vehicle capacity.
- **Response `200 OK`**:
```json
{
  "data": {
    "plan_summary": {
      "total_passengers_external": 740,
      "total_runs_required": 52,
      "total_runs_capacity": 48,
      "shortage_runs": 4,
      "is_capacity_deficit": true
    },
    "property_plans": [
      {
        "property_id": "EXT04",
        "property_name": "Lakeview Hotel",
        "distance_km": 9.0,
        "transport_availability": "limited",
        "risk_level": "HIGH",
        "windows": [
          {
            "window_start": "2026-10-31T00:00:00Z",
            "window_end": "2026-10-31T01:00:00Z",
            "passengers": 28,
            "required_runs": 2,
            "confirmed_runs": 1,
            "shortage": 1,
            "is_uncovered": true
          }
        ]
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/transport/shuttles/runs`
- **Description**: Lists scheduled, in-transit, and completed shuttle runs.
- **Query Parameters**:
  - `property_id` (string, optional)
  - `status` (string, optional: `SCHEDULED`, `IN_TRANSIT`, `COMPLETED`, `CANCELLED`)
  - `date` (string, optional: YYYY-MM-DD)
- **Response `200 OK`**:
```json
{
  "data": {
    "runs": [
      {
        "id": "run_001",
        "route_name": "Campus to Lakeview Hotel",
        "vehicle_id": "trn_01",
        "vehicle_number": "MP-09-AB-1234",
        "departure_at": "2026-10-31T00:15:00Z",
        "arrival_at": "2026-10-31T00:45:00Z",
        "capacity": 15,
        "passengers_assigned": 14,
        "escort_staff_id": "ST02",
        "status": "SCHEDULED"
      }
    ],
    "total": 36
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/transport/shuttles/runs`
- **Description**: Creates or dispatches a shuttle run via ChangeService (`transport.create_run`).
- **Request Body**:
```json
{
  "payload": {
    "route_name": "Campus to Maa Sarada Hostel",
    "vehicle_id": "trn_02",
    "property_id": "EXT02",
    "departure_at": "2026-10-31T23:30:00Z",
    "arrival_at": "2026-10-31T23:55:00Z",
    "capacity": 15,
    "escort_staff_id": "ST10"
  },
  "reason": "Scheduled night shuttle for external contingent"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_run_new_01",
    "status": "APPLIED",
    "data": {
      "run_id": "run_042",
      "status": "SCHEDULED"
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/transport/safety/night-roster`
- **Description**: Returns all late-night arrivals/departures, identifying external property residents with unverified safety arrangements.
- **Response `200 OK`**:
```json
{
  "data": {
    "late_night_movements": [
      {
        "participant_id": "par_0412",
        "name": "Kavita Rao",
        "contingent_name": "IIT Bombay",
        "property_id": "EXT04",
        "property_name": "Lakeview Hotel",
        "scheduled_time": "2026-10-31T00:30:00Z",
        "movement_type": "DEPARTURE",
        "is_minor": true,
        "shuttle_assigned": false,
        "escort_assigned": false,
        "safety_verified": false
      }
    ],
    "total_unverified": 14
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/transport/safety/verify`
- **Description**: Marks a participant's night transport and escort arrangement verified via ChangeService (`transport.verify_safety`).
- **Request Body**:
```json
{
  "payload": {
    "participant_id": "par_0412",
    "shuttle_run_id": "run_001",
    "escort_staff_id": "ST02",
    "verified": true,
    "notes": "Verified boarding with coordinator escort"
  },
  "reason": "Volunteer confirmed participant safety checklist"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_verify_01",
    "status": "APPLIED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `GET /api/v1/transport/guardians/queue`
- **Description**: Dedicated approval queue for minors (<18 years old) residing in external accommodation properties.
- **Query Parameters**:
  - `status` (string, optional: `PENDING`, `APPROVED`, `REJECTED`)
  - `property_id` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "minors_queue": [
      {
        "approval_id": "gdn_001",
        "participant_id": "par_0188",
        "participant_name": "Rohan Mehra",
        "age": 17,
        "contingent_id": "C05",
        "contingent_name": "BITS Pilani",
        "property_id": "EXT03",
        "property_name": "Central Residency",
        "stay_duration_days": 4,
        "approval_status": "PENDING",
        "escort_staff_id": "ST07",
        "escort_staff_name": "Meera Khan",
        "transport_arrangement": "Assigned Shuttle Run run_003",
        "responsible_coordinator_id": "ST02",
        "responsible_coordinator_name": "Ananya Patel"
      }
    ],
    "total": 71,
    "pending_count": 71
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `POST /api/v1/transport/guardians/{id}/approve`
- **Description**: Approves or rejects guardian authorization for a minor's external accommodation stay via ChangeService (`transport.approve_guardian`).
- **Request Body**:
```json
{
  "payload": {
    "approval_status": "APPROVED",
    "notes": "Signed guardian consent received and verified with contingent escort"
  },
  "reason": "Parental consent form verified"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_gdn_appr_01",
    "status": "APPLIED"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.10 `GET /api/v1/transport/alerts`
- **Description**: Surfaces high-priority plain-text transport and safety alerts.
- **Response `200 OK`**:
```json
{
  "data": {
    "alerts": [
      "14 participants are scheduled to leave Lakeview Hotel at 00:30, but no verified shuttle is assigned.",
      "71 minors in external accommodation are pending guardian and escort verification.",
      "Peak departure window on 2026-11-02 18:00 has a deficit of 3 shuttle runs (45 passengers uncovered)."
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.11 `GET /api/v1/transport/coverage/summary`
- **Description**: High-level safety coverage summary across participants, shuttles, escorts, and external properties.
- **Response `200 OK`**:
```json
{
  "data": {
    "people_requiring_transport": 740,
    "confirmed_shuttle_capacity": 600,
    "uncovered_transport_requests": 140,
    "late_night_movements": 42,
    "pending_minor_approvals": 71,
    "unassigned_escorts": 18,
    "property_risks": [
      {
        "property_id": "EXT04",
        "name": "Lakeview Hotel",
        "risk_level": "HIGH",
        "reason": "9km distance and limited commercial transport availability"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.12 `GET /api/v1/transport/feasibility`
- **Description**: Checks whether transportation is feasible for an external property at a specific timestamp.
- **Query Parameters**:
  - `property_id` (string, required)
  - `time` (ISO datetime string, required)
- **Response `200 OK`**:
```json
{
  "data": {
    "property_id": "EXT04",
    "time": "2026-10-31T00:30:00Z",
    "is_feasible": false,
    "reason": "Outside standard transport hours (06:00-24:00) with no scheduled dedicated shuttle run"
  },
  "meta": {},
  "warnings": []
}
```
