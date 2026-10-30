# API Specification: `accommodation`

> Owner: `@P2` (shared with `@P3` for UI)  
> Base Path: `/api/v1/accommodation`  
> Status: `REVIEW`

---

## 1. Overview
The Accommodation module manages on-campus hostels (710 beds across 200 rooms), 6 external properties (740 beds), automated candidate plan generation (Plan A: Cohesion-First, Plan B: Cost-First, Plan C: Balanced), explainable shortage diagnosis ("Why-not?"), full occupancy map visualization, and operational constraint-checked bed assignment/relocation.

---

## 2. Endpoints

### 2.1 `GET /api/v1/accommodation/plans`
- **Description**: Fetch all generated candidate plans (Plan A, B, C) and current LIVE plan with comparison metrics.
- **Response `200 OK`**:
```json
{
  "data": {
    "plans": [
      {
        "plan_id": "plan_A_cohesion",
        "kind": "A",
        "status": "CANDIDATE",
        "name": "Plan A: Cohesion-First",
        "on_campus_placed": 710,
        "external_placed": 1284,
        "unplaced_count": 150,
        "contingent_splits": 4,
        "total_cost_inr": 3315700,
        "safety_flags_count": 12,
        "accessibility_issues_count": 2,
        "relaxed_constraints_count": 8,
        "sacrifices_summary": "Sacrifices budget expenditure (₹33,15,700) to keep contingents unified within the same buildings.",
        "created_at": "2026-10-30T10:00:00Z"
      },
      {
        "plan_id": "plan_B_cost",
        "kind": "B",
        "status": "CANDIDATE",
        "name": "Plan B: Cost-First",
        "on_campus_placed": 710,
        "external_placed": 1342,
        "unplaced_count": 92,
        "contingent_splits": 19,
        "total_cost_inr": 2480000,
        "safety_flags_count": 28,
        "accessibility_issues_count": 4,
        "relaxed_constraints_count": 31,
        "sacrifices_summary": "Sacrifices contingent cohesion and group proximity to minimize external hotel booking costs.",
        "created_at": "2026-10-30T10:00:00Z"
      },
      {
        "plan_id": "plan_C_balanced",
        "kind": "C",
        "status": "CANDIDATE",
        "name": "Plan C: Balanced (Recommended)",
        "on_campus_placed": 710,
        "external_placed": 1318,
        "unplaced_count": 116,
        "contingent_splits": 8,
        "total_cost_inr": 2890000,
        "safety_flags_count": 14,
        "accessibility_issues_count": 1,
        "relaxed_constraints_count": 12,
        "sacrifices_summary": "Balanced compromises: permits minor contingent splits only when hotel cost exceeds threshold.",
        "created_at": "2026-10-30T10:00:00Z"
      }
    ],
    "budget_ceiling_inr": null,
    "is_budget_unset": true
  },
  "meta": {},
  "warnings": ["External Accommodation Budget is unset. Engine running in unconstrained mode."]
}
```

---

### 2.2 `POST /api/v1/accommodation/generate-plan`
- **Description**: Trigger optimization engine to generate candidate plan with custom weights and parameters.
- **Request Body**:
```json
{
  "kind": "C",
  "cleaning_buffer_minutes": 180,
  "max_distance_km": 15,
  "allow_split_contingents": true,
  "weights": {
    "cohesion": 0.5,
    "cost": 0.3,
    "travel": 0.2
  }
}
```
- **Response `200 OK`**: Returns generated plan summary.

---

### 2.3 `GET /api/v1/accommodation/shortages`
- **Description**: Retrieve unplaced participants grouped by blocking reason, contingent, accessibility need, and housing preference.
- **Response `200 OK`**:
```json
{
  "data": {
    "total_unplaced": 116,
    "grouped_by_reason": [
      {
        "reason_code": "UNKNOWN_GENDER",
        "title": "Gender Unknown (Safety Gate #2)",
        "count": 48,
        "description": "Room allocation cannot enforce campus hostel gender segregation safety rules.",
        "affected_contingents": ["C05", "C08", "C12", "C15"],
        "criticality": "HIGH"
      },
      {
        "reason_code": "HARD_ACCESSIBILITY",
        "title": "Ground-Floor Accessible Room Deficit",
        "count": 14,
        "description": "Participants with wheelchair/mobility needs exceed available ground-floor ramped rooms.",
        "affected_contingents": ["C01", "C05", "C19"],
        "criticality": "CRITICAL"
      },
      {
        "reason_code": "EXTERNAL_CAPACITY_EXHAUSTED",
        "title": "External Property Room Exhaustion",
        "count": 34,
        "description": "Remaining demand exceeds available bed blocks in verified nearby properties.",
        "affected_contingents": ["C08", "C27", "C38"],
        "criticality": "MEDIUM"
      },
      {
        "reason_code": "MINOR_ESCORT_RESTRICTION",
        "title": "Minor Participant Off-Campus Restriction",
        "count": 20,
        "description": "Minors (<18) without verified faculty escorts cannot be placed in off-campus hotels.",
        "affected_contingents": ["C05", "C18", "C32"],
        "criticality": "HIGH"
      }
    ],
    "unplaced_items": [
      {
        "participant_id": "P0104",
        "name": "Sneha Mukherjee",
        "contingent_id": "C05",
        "college": "IIT Bombay",
        "blocking_reason": "UNKNOWN_GENDER",
        "accessibility_needed": false,
        "housing_preference": "UNKNOWN",
        "gender": "UNKNOWN"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/accommodation/why-not/{participant_id}`
- **Description**: Explainable diagnostic panel detailing why a participant cannot be accommodated.
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0104",
    "name": "Sneha Mukherjee",
    "contingent_id": "C05",
    "blocking_requirement": "Rule 2: Gender-Appropriate Allocation & Safety Policy",
    "missing_information": "Gender attribute is UNKNOWN in raw import dataset.",
    "rejected_options": [
      { "location": "Hostel 3 (Wing B)", "reason": "Boys hostel block: cannot place without gender confirmation" },
      { "location": "Hostel 4 (Wing A)", "reason": "Girls hostel block: cannot place without gender confirmation" },
      { "location": "Hotel Radisson Rau", "reason": "Property gender suitability flag is UNVERIFIED" }
    ],
    "counterfactual_impact": "If verified as 'Female', 4 beds in Hostel 4 (Wing A, Room 204) become immediately assignable alongside contingent peers.",
    "verification_target": {
      "field": "gender",
      "entity_id": "P0104"
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/accommodation/occupancy`
- **Description**: Occupancy matrix of on-campus blocks, floors, and external properties.
- **Response `200 OK`**:
```json
{
  "data": {
    "blocks": [
      {
        "block_id": "H3",
        "name": "Hostel 3 (Boys Block)",
        "gender_class": "boys",
        "total_beds": 360,
        "occupied_beds": 348,
        "cleaning_beds": 6,
        "closed_beds": 2,
        "free_beds": 4,
        "floors": [
          {
            "floor_number": 0,
            "is_ground": true,
            "rooms": [
              {
                "room_id": "H3-101",
                "room_number": "101",
                "accessible": true,
                "status": "AVAILABLE",
                "cleaning_status": "READY",
                "beds": [
                  { "bed_id": "H3-101-A", "status": "OCCUPIED", "contingent_id": "C05", "contingent_color": "#6366f1", "participant_id": "P0102", "participant_name": "Aarav Sharma", "version": 1 },
                  { "bed_id": "H3-101-B", "status": "FREE", "version": 1 }
                ]
              }
            ]
          }
        ]
      }
    ],
    "external_properties": [
      {
        "property_id": "ext_01",
        "name": "Radisson Blu Rau",
        "total_beds": 200,
        "occupied_beds": 184,
        "cost_per_bed_night": 2800,
        "distance_km": 11.5,
        "accessibility_verified": false,
        "gender_suitability_verified": false,
        "transport_limited": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `POST /api/v1/accommodation/check-constraints`
- **Description**: Live pre-flight check evaluating violated and relaxed constraints before bed assignment or transfer.
- **Request Body**:
```json
{
  "participant_id": "P0104",
  "target_bed_id": "H3-101-B"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "allowed": false,
    "is_hard_violation": true,
    "violations": [
      {
        "code": "GENDER_MISMATCH_SAFETY",
        "severity": 4,
        "hard": true,
        "message": "Hostel 3 is a Boys block. Participant P0104 has UNKNOWN gender; assignment violates hard campus safety rule #2."
      }
    ],
    "relaxed_soft_constraints": [
      {
        "code": "CONTINGENT_COHESION",
        "message": "Assignment places participant next to contingent leader Rohan Deshmukh (Room 101)."
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/accommodation/assign`
- **Description**: Assign or move participant to bed/room with mandatory justification.
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Director approved buffer room allocation for delayed contingent arrival",
  "dry_run": false,
  "payload": {
    "participant_id": "P0102",
    "target_bed_id": "H3-101-A",
    "plan_id": "plan_C_balanced",
    "override_hard_constraint": false
  }
}
```
- **Response `200 OK`**: Returns updated assignment and WhyCard.
- **Response `409 Conflict`**: Version conflict when bed is modified concurrently.
```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "This bed was assigned or updated by another coordinator. Please refresh the occupancy map."
  }
}
```

---

### 2.8 `POST /api/v1/accommodation/commit-live`
- **Description**: Promote candidate plan (Plan A, B, or C) to LIVE operational state.
- **Request Body**:
```json
{
  "expected_version": 1,
  "plan_id": "plan_C_balanced",
  "reason": "Finalized after Accommodation Lead & Finance Lead review"
}
```
- **Response `200 OK`**: Plan committed to live state.
