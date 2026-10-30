# API Specification: `unknowns` (Field Verification)

> Owner: `P2` (P1 implementing field-verification parts for participants)  
> Base Path: `/api/v1/unknowns`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `unknowns` module enforces FestOS Principle #4: **"UNKNOWN is a first-class value. A blank never means NO, consent, a gender, dietary clearance or absence of need."**
Key capabilities:
- **Field Verification Queue**: Real-time aggregation of unresolved `UNKNOWN` fields ranked deterministically by `Count x Criticality` (e.g., housing request criticality: 4, diet: 3, tshirt size: 2).
- **Value-of-Information (VOI) Ranking Engine**: Simulates outcomes across field groups (housing preference/gender, accessibility, diet, arrival/departure, guardian/escort, merchandise size) by re-running allocation and vendor coverage in sandboxes. Reports ranges and explicit distributions for beds made eligible, unplaced participants reduced, cost deltas, and safety uncertainty reduction.
- **Minimal Confirmation Requests**: Batched verification packages tailored for contingent leaders or reception volunteers containing only the minimum information needed.
- **Verified Value Recording**: Mutations committed strictly through `ChangeService` (`unknowns.verify_field`), capturing verifier, source (e.g., `DESK_VERIFICATION`, `LEADER_SIGN_OFF`, `PHONE_CONFIRMATION`), and timestamp.
- **Why-Not Simulation**: Extends unplaced participant explanations with counterfactual predictions: "What confirming X would change".

---

## 2. Endpoints

### 2.1 `GET /api/v1/unknowns/queue`
- **Description**: Returns the operational queue of unresolved unknown fields grouped and ranked by `count x criticality`.
- **Response `200 OK`**:
```json
{
  "data": {
    "total_unresolved_fields": 1284,
    "queue": [
      {
        "field": "accommodation_requested",
        "entity_type": "participant",
        "count": 418,
        "criticality": 4,
        "score": 1672,
        "owner": "ACCOMMODATION_LEAD",
        "impact_text": "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
        "sample_entity_ids": ["P0012", "P0045", "P0102"]
      },
      {
        "field": "gender",
        "entity_type": "participant",
        "count": 417,
        "criticality": 4,
        "score": 1668,
        "owner": "ACCOMMODATION_LEAD",
        "impact_text": "Room allocation cannot enforce campus gender segregation safety constraints.",
        "sample_entity_ids": ["P0003", "P0019"]
      },
      {
        "field": "diet",
        "entity_type": "participant",
        "count": 394,
        "criticality": 3,
        "score": 1182,
        "owner": "FOOD_OPS_MANAGER",
        "impact_text": "Catering procurement buffers risk meal shortages or food waste.",
        "sample_entity_ids": ["P0001", "P0005"]
      },
      {
        "field": "tshirt_size",
        "entity_type": "participant",
        "count": 55,
        "criticality": 2,
        "score": 110,
        "owner": "MERCHANDISE_MANAGER",
        "impact_text": "Merchandise packing desk cannot pre-kit kit bags for arrival check-in.",
        "sample_entity_ids": ["P0211"]
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/unknowns/items`
- **Description**: Query individual participant records with unresolved unknown fields.
- **Query Parameters**:
  - `field` (string, required): e.g., `diet`, `gender`, `accommodation_requested`
  - `contingent_id` (string, optional): Filter by contingent
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "P0001",
        "name": "Rohan Deshmukh",
        "contingent_id": "C05",
        "field": "diet",
        "current_value": "UNKNOWN",
        "status": "UNKNOWN",
        "owner": "FOOD_OPS_MANAGER"
      }
    ],
    "total": 394,
    "page": 1,
    "page_size": 50,
    "total_pages": 8
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/unknowns/verify`
- **Description**: Record a verified field value through `ChangeService` (`unknowns.verify_field`). Updates the target entity and appends to `field_verification`.
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Participant confirmed dietary preference in person at reception desk",
  "dry_run": false,
  "payload": {
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet",
    "value": "VEG",
    "source": "DESK_VERIFICATION",
    "verifier": "usr_desk_vol01"
  }
}
```
- **Response `200 OK`**: Standard Envelope containing `ChangeResult`.

---

### 2.4 `POST /api/v1/unknowns/token`
- **Description**: Issue a cryptographically signed, expiring token enabling a contingent leader or desk volunteer to submit verified values without full system access.
- **Request Body**:
```json
{
  "entity_type": "participant",
  "entity_id": "P0001",
  "field": "diet",
  "expires_in_minutes": 1440,
  "recipient_role": "LEADER"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "token": "eyJh...signed_token...",
    "expires_at": "2026-10-31T18:00:00Z",
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/unknowns/confirm/{token}`
- **Description**: Public verification endpoint using a signed confirmation token. Commits the verified value through `ChangeService`.
- **Request Body**:
```json
{
  "value": "VEG",
  "source": "LEADER_TOKEN_SUBMISSION",
  "comment": "Confirmed by contingent leader Rohan Deshmukh"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "VERIFIED",
    "entity_id": "P0001",
    "field": "diet",
    "value": "VEG",
    "verified_at": "2026-10-30T14:22:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/unknowns/history/{entity_type}/{entity_id}/{field}`
- **Description**: Retrieve chronological verification and status progression for a specific field on an entity.
- **Response `200 OK`**:
```json
{
  "data": {
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet",
    "verifications": [
      {
        "id": "ver_98765",
        "status": "VERIFIED",
        "value": "VEG",
        "source": "LEADER_TOKEN_SUBMISSION",
        "verified_by": "LEADER_TOKEN",
        "verified_at": "2026-10-30T14:22:00Z"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/unknowns/ranking`
- **Description**: Value-of-Information (VOI) ranking across unknown field groups. Simulates sandbox outcomes for each plausible value/distribution and measures beds made eligible, unplaced participants reduced, cost change, cohesion gain, dietary coverage gain, and safety uncertainty reduction.
- **Response `200 OK`**:
```json
{
  "data": {
    "ranked_groups": [
      {
        "group_id": "housing_gender",
        "group_name": "Housing Preference & Gender",
        "fields": ["accommodation_requested", "gender"],
        "affected_participants": 418,
        "operational_improvement_score": 92.4,
        "rank": 1,
        "method": "DATA_DISTRIBUTION",
        "simulated_outcomes": {
          "beds_eligible_range": [65, 110],
          "unplaced_reduced_range": [35, 78],
          "cost_delta_inr_range": [-45000.0, 12000.0],
          "cohesion_gain_pct": 18.5,
          "dietary_coverage_gain_pct": 0.0,
          "safety_uncertainty_reduction_pct": 85.0
        },
        "summary": "Confirming housing preferences for these 418 participants makes 65-110 beds eligible and reduces unplaced participants by 35-78."
      },
      {
        "group_id": "accessibility",
        "group_name": "Accessibility Needs",
        "fields": ["accessibility_needs"],
        "affected_participants": 32,
        "operational_improvement_score": 88.0,
        "rank": 2,
        "method": "BOUNDING_RANGE",
        "simulated_outcomes": {
          "beds_eligible_range": [10, 25],
          "unplaced_reduced_range": [8, 20],
          "cost_delta_inr_range": [0.0, 15000.0],
          "cohesion_gain_pct": 5.0,
          "dietary_coverage_gain_pct": 0.0,
          "safety_uncertainty_reduction_pct": 98.0
        },
        "summary": "Confirming accessibility needs prevents high-severity ground-floor room reassignments."
      },
      {
        "group_id": "dietary",
        "group_name": "Dietary Requirement",
        "fields": ["diet"],
        "affected_participants": 394,
        "operational_improvement_score": 74.2,
        "rank": 3,
        "method": "DATA_DISTRIBUTION",
        "simulated_outcomes": {
          "beds_eligible_range": [0, 0],
          "unplaced_reduced_range": [0, 0],
          "cost_delta_inr_range": [-12000.0, 5000.0],
          "cohesion_gain_pct": 0.0,
          "dietary_coverage_gain_pct": 42.0,
          "safety_uncertainty_reduction_pct": 40.0
        },
        "summary": "Confirming dietary choices eliminates meal-slot deficits across 14 vendors."
      },
      {
        "group_id": "arrival_departure",
        "group_name": "Arrival & Departure Timings",
        "fields": ["travel_arrival", "travel_departure"],
        "affected_participants": 210,
        "operational_improvement_score": 68.5,
        "rank": 4,
        "method": "DATA_DISTRIBUTION",
        "simulated_outcomes": {
          "beds_eligible_range": [20, 45],
          "unplaced_reduced_range": [15, 30],
          "cost_delta_inr_range": [-8000.0, 2000.0],
          "cohesion_gain_pct": 8.0,
          "dietary_coverage_gain_pct": 12.0,
          "safety_uncertainty_reduction_pct": 60.0
        },
        "summary": "Confirming arrival times resolves cleaning buffer overlaps and shuttle planning."
      },
      {
        "group_id": "guardian_escort",
        "group_name": "Guardian / Escort Info",
        "fields": ["guardian_phone", "escort_name"],
        "affected_participants": 71,
        "operational_improvement_score": 65.0,
        "rank": 5,
        "method": "BOUNDING_RANGE",
        "simulated_outcomes": {
          "beds_eligible_range": [0, 0],
          "unplaced_reduced_range": [0, 0],
          "cost_delta_inr_range": [0.0, 0.0],
          "cohesion_gain_pct": 0.0,
          "dietary_coverage_gain_pct": 0.0,
          "safety_uncertainty_reduction_pct": 95.0
        },
        "summary": "Validates minor curfew duty-of-care and overnight stay permissions."
      },
      {
        "group_id": "merch_size",
        "group_name": "Merchandise Size",
        "fields": ["tshirt_size"],
        "affected_participants": 55,
        "operational_improvement_score": 38.0,
        "rank": 6,
        "method": "DATA_DISTRIBUTION",
        "simulated_outcomes": {
          "beds_eligible_range": [0, 0],
          "unplaced_reduced_range": [0, 0],
          "cost_delta_inr_range": [-2500.0, 1000.0],
          "cohesion_gain_pct": 0.0,
          "dietary_coverage_gain_pct": 0.0,
          "safety_uncertainty_reduction_pct": 10.0
        },
        "summary": "Allows pre-kitting kits to avoid check-in desk queues."
      }
    ],
    "total_groups": 6
  },
  "meta": {
    "total_unresolved_participants": 680,
    "methodology": "Pure scenario sandbox replay with bounding range & empirical data distributions"
  },
  "warnings": []
}
```

---

### 2.8 `POST /api/v1/unknowns/confirmation-requests`
- **Description**: Generates minimal confirmation request packages batched by contingent leader or desk volunteer, requesting only the specific missing fields needed.
- **Request Body**:
```json
{
  "target_type": "CONTINGENT_LEADER",
  "contingent_id": "C05",
  "group_id": "housing_gender"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "contingent_id": "C05",
    "leader_name": "Rohan Deshmukh",
    "batch_token": "eyJh...signed...",
    "expires_at": "2026-10-31T20:00:00Z",
    "fields_requested": ["accommodation_requested", "gender"],
    "participants": [
      {
        "id": "P0012",
        "name": "Ananya Sen",
        "missing_fields": ["gender", "accommodation_requested"]
      }
    ],
    "total_participants": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `GET /api/v1/unknowns/why-not/{participant_id}`
- **Description**: Diagnostic explanation extending Why-Not with simulated counterfactual predictions: "What confirming field X would change for this participant".
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "P0012",
    "name": "Ananya Sen",
    "current_status": "UNPLACED",
    "blocking_reasons": ["GENDER_UNKNOWN", "HOUSING_PREFERENCE_UNKNOWN"],
    "counterfactuals": [
      {
        "field": "gender",
        "if_confirmed_as": "FEMALE",
        "outcome": "Eligible for 42 on-campus beds in Hostel Block A",
        "can_be_placed": true
      },
      {
        "field": "accommodation_requested",
        "if_confirmed_as": "NO",
        "outcome": "Removed from shortage queue; 0 beds required",
        "can_be_placed": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
