# API Specification: `accommodation`

> Owner: `@P2` (shared with `@P3` for UI)  
> Base Path: `/api/v1/accommodation`  
> Status: `APPROVED`

---

## 1. Overview
The Accommodation module manages on-campus hostels (710 beds across 200 rooms), 6 external properties (740 beds), automated deterministic candidate plan generation (Plan A: Cohesion-First, Plan B: Cost-First, Plan C: Balanced), rolling occupancy tracking with cleaning buffers, explainable shortage diagnosis ("Why-not?"), bed demand timelines, and decision cards.

Engine logic in `app/engines/accommodation/` is pure: dataclass snapshots in, plan objects out. `app/services/accommodation/` wraps the engine with database access and public interfaces. Candidate plans are not live. Live-plan commit, check-in, and manual overrides belong to Prompt 8.

---

## 2. Endpoints

### 2.1 `POST /api/v1/accommodation/plans/generate`
- **Description**: Triggers deterministic accommodation engine to generate candidate plans (A, B, C or specific kinds).
- **Request Body**:
```json
{
  "kinds": ["A", "B", "C"],
  "params": {
    "cleaning_buffer_minutes": 180,
    "budget_inr": null,
    "solver": "greedy",
    "weights": {
      "cohesion": 0.5,
      "cost": 0.3,
      "travel": 0.2
    }
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "generated_plans": [
      {
        "plan_id": "plan_A_cohesion",
        "kind": "A",
        "status": "CANDIDATE",
        "name": "Plan A: Cohesion-First",
        "plan_hash": "a1b2c3d4e5f67890",
        "on_campus_count": 861,
        "external_count": 920,
        "unplaced_count": 360,
        "contingent_splits": 36,
        "total_cost_inr": 3315700,
        "safety_flags_count": 0,
        "accessibility_issues_count": 109,
        "relaxed_constraints_count": 36,
        "minors_external_count": 71,
        "created_at": "2026-10-30T10:00:00Z"
      }
    ],
    "is_budget_unset": true
  },
  "meta": { "total": 3 },
  "warnings": ["External Accommodation Budget is unset. Engine running in budget-unset mode."]
}
```

---

### 2.2 `GET /api/v1/accommodation/plans`
- **Description**: List all generated candidate plans and summaries.
- **Query Params**: `status` (optional: CANDIDATE, APPROVED, LIVE, ARCHIVED).
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
        "plan_hash": "a1b2c3d4e5f67890",
        "on_campus_count": 861,
        "external_count": 920,
        "unplaced_count": 360,
        "contingent_splits": 36,
        "total_cost_inr": 3315700,
        "safety_flags_count": 0,
        "accessibility_issues_count": 109,
        "relaxed_constraints_count": 36,
        "minors_external_count": 71,
        "sacrifices_summary": "Prioritizes keeping contingents together, allowing cost overflow."
      }
    ]
  },
  "meta": { "total": 3 },
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/accommodation/plans/{id}`
- **Description**: Fetch detailed plan metrics, decision cards, assignments sample, and constraint breakdown for a specific plan.
- **Response `200 OK`**:
```json
{
  "data": {
    "plan_id": "plan_A_cohesion",
    "kind": "A",
    "status": "CANDIDATE",
    "name": "Plan A: Cohesion-First",
    "plan_hash": "a1b2c3d4e5f67890",
    "metrics": {
      "on_campus_count": 861,
      "external_count": 920,
      "unplaced_count": 360,
      "contingent_splits": 36,
      "total_cost_inr": 3315700,
      "safety_flags_count": 0,
      "accessibility_issues_count": 109,
      "relaxed_constraints_count": 36,
      "minors_external_count": 71
    },
    "decision_card": {
      "id": "card_plan_A_cohesion",
      "subject": "Plan A: Cohesion-First Candidate",
      "recommendation": "Use for high-cohesion festival experience if budget allows ₹33,15,700.",
      "hard_satisfied": ["gender_separation", "wheelchair_accessible_rooms", "ground_floor_rooms"],
      "soft_relaxed": [
        { "constraint": "contingent_cohesion", "reason": "36 contingents split across hostel wings due to capacity" }
      ],
      "alternatives_rejected": [
        { "option": "Assign unknown gender to boys block", "why": "Hard safety violation #2" }
      ],
      "cost_impact": 3315700,
      "people_affected": 2141
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/accommodation/plans/compare?ids=`
- **Description**: Compare multiple candidate plans (e.g. Plan A, Plan B, Plan C) side-by-side across all key dimensions.
- **Query Params**: `ids` (comma-separated plan IDs, e.g. `plan_A_cohesion,plan_B_cost,plan_C_balanced`).
- **Response `200 OK`**:
```json
{
  "data": {
    "plans": [
      {
        "plan_id": "plan_A_cohesion",
        "kind": "A",
        "name": "Plan A: Cohesion-First",
        "on_campus_count": 861,
        "external_count": 920,
        "unplaced_count": 360,
        "contingent_splits": 36,
        "total_cost_inr": 3315700,
        "minors_external_count": 71
      },
      {
        "plan_id": "plan_B_cost",
        "kind": "B",
        "name": "Plan B: Cost-First",
        "on_campus_count": 861,
        "external_count": 920,
        "unplaced_count": 360,
        "contingent_splits": 36,
        "total_cost_inr": 3319250,
        "minors_external_count": 71
      },
      {
        "plan_id": "plan_C_balanced",
        "kind": "C",
        "name": "Plan C: Balanced",
        "on_campus_count": 861,
        "external_count": 920,
        "unplaced_count": 360,
        "contingent_splits": 36,
        "total_cost_inr": 3317475,
        "minors_external_count": 71
      }
    ],
    "trade_offs_summary": "Plan A minimizes contingent splitting; Plan B prioritizes cheaper properties; Plan C balances cohesion and travel distance."
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/accommodation/plans/{id}/shortages` (and `GET /api/v1/accommodation/shortages`)
- **Description**: Retrieve unplaced participants for a candidate plan grouped by the fixed taxonomy:
  - `HARD_ACCESSIBILITY`
  - `GENDER_OR_HOUSING_UNKNOWN`
  - `TRANSPORT_RESTRICTED`
  - `NO_ELIGIBLE_PROPERTY`
  - `BUDGET`
  - `MISSING_INFO`
  - `CAPACITY`
- **Response `200 OK`**:
```json
{
  "data": {
    "plan_id": "plan_A_cohesion",
    "total_unplaced": 360,
    "breakdown": {
      "HARD_ACCESSIBILITY": 109,
      "TRANSPORT_RESTRICTED": 129,
      "NO_ELIGIBLE_PROPERTY": 122,
      "GENDER_OR_HOUSING_UNKNOWN": 241
    },
    "items": [
      {
        "participant_id": "P0042",
        "name": "Ananya Roy",
        "contingent_id": "C05",
        "blocking_reasons": ["GENDER_OR_HOUSING_UNKNOWN"],
        "rejected_options": [
          { "target": "Hostel 1 (Boys)", "reason": "Gender segregation policy" },
          { "target": "Hostel 2 (Girls)", "reason": "Gender attribute is UNKNOWN" }
        ],
        "counterfactual": "If gender is confirmed as Female, 12 beds in Hostel 2 become eligible."
      }
    ]
  },
  "meta": { "total": 360 },
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/accommodation/why-not/{participant_id}?plan_id=`
- **Description**: Explainable diagnostic panel detailing why a participant is unplaced in a given plan, rejected alternatives, and counterfactuals.
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0042",
    "plan_id": "plan_A_cohesion",
    "placed": false,
    "blocking_reasons": ["GENDER_OR_HOUSING_UNKNOWN"],
    "details": "Participant has UNKNOWN gender; safety rule #2 prohibits placement into gendered hostel blocks.",
    "rejected_options": [
      { "entity": "Hostel 1", "reason": "Boys hostel block" },
      { "entity": "Hostel 2", "reason": "Girls hostel block" },
      { "entity": "Radisson Blu Rau", "reason": "Unverified gender suitability" }
    ],
    "counterfactual": {
      "field": "gender",
      "test_value": "Female",
      "result": "Eligible for Hostel 2 (Girls Block); 4 beds available."
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/accommodation/demand-timeline`
- **Description**: Returns hourly bed demand timeline across festival dates, distinguishing CONFIRMED demand (accommodation_requested = YES) vs POSSIBLE demand (accommodation_requested = UNKNOWN), and listing invalid intervals excluded.
- **Response `200 OK`**:
```json
{
  "data": {
    "peak_simultaneous_demand": 1601,
    "peak_timestamp": "2026-10-30T18:00:00Z",
    "confirmed_requests_count": 2141,
    "possible_requests_count": 312,
    "invalid_intervals": [
      {
        "participant_id": "P0037",
        "arrival": "2026-11-02T10:00:00Z",
        "departure": "2026-10-29T10:00:00Z",
        "reason": "Arrival is after departure"
      }
    ],
    "timeline": [
      {
        "timestamp": "2026-10-30T18:00:00Z",
        "confirmed_demand": 1601,
        "possible_demand": 240,
        "total_demand": 1841,
        "on_campus_capacity": 710,
        "total_capacity": 1450
      }
    ]
  },
  "meta": {},
  "warnings": ["3 records excluded from plan generation due to invalid stay intervals."]
}
```

---

### 2.8 `GET /api/v1/accommodation/rooms`
- **Description**: Returns all campus hostel rooms (710 beds across 200 rooms) with floor, gender class, accessibility tags, and status.
- **Query Params**: `block`, `accessible`, `floor`.

---

### 2.9 `GET /api/v1/accommodation/properties`
- **Description**: Returns all external properties (740 beds across 6 properties) with bed count, cost per bed night, distance, travel time, and verification flags.
- **Response `200 OK`**:
```json
{
  "data": [
    {
      "property_id": "EP01",
      "name": "Hotel Radisson Rau",
      "total_beds": 200,
      "cost_per_bed_night": 2800,
      "distance_km": 11.5,
      "travel_time_min": 25,
      "accessibility_verified": false,
      "gender_suitability_verified": false,
      "transport_limited": true
    }
  ],
  "meta": { "total": 6 },
  "warnings": []
}
```

---

### 2.10 `GET /api/v1/accommodation/occupancy`
- **Description**: Full occupancy map showing block/floor room statuses, beds, cleaning readiness, and current candidate plan allocations.
