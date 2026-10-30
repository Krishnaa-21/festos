# API Specification: `decisions`

> Owner: `P1`  
> Base Path: `/api/v1/decisions`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Decision Log and Explainability Service** captures all high-impact operational decisions made across the festival—spanning accommodation allocation, schedule adjustments, vendor replacements, incident interventions, and emergency overrides.

Key capabilities:
- **DecisionCard Structure**:
  - Why the decision was chosen over other options.
  - Hard constraints satisfied (e.g. accessibility, gender segregation, legal working limits).
  - Soft constraints relaxed (e.g. contingent cohesion split, proximity).
  - Alternatives considered and rejected with explicit rationales.
  - Financial cost impact and participant count affected.
  - Approving authority and audit reference.
- **Link to Overrides**: Decisions resulting from manual operator overrides link directly to the P3 `override` register via `override_id` without duplicating data.
- **Explainable "Why" Endpoint**: One-click drill-down for any decision card providing full contextual clarity for festival organizers, auditors, and contingent leaders.
- **Helper Integration**: Exposes `decision_log.add(...)` in Python for seamless recording from all domain engines.

---

## 2. Endpoints

### 2.1 `GET /api/v1/decisions`
- **Description**: Lists recorded decision cards, with filters by module, approver, and date range.
- **Query Parameters**:
  - `module` (string, optional: e.g. `accommodation`, `schedule`, `vendors`, `incidents`, `overrides`)
  - `approver` (string, optional: user ID or name)
  - `from_date` (string, optional: YYYY-MM-DD)
  - `to_date` (string, optional: YYYY-MM-DD)
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
- **Response `200 OK`**:
```json
{
  "data": {
    "decisions": [
      {
        "id": "dec_accom_041",
        "module": "accommodation",
        "decision_type": "EXTERNAL_PROPERTY_SPILLOVER",
        "title": "Placed IIT Bombay Contingent (18 pax) in Lakeview Hotel",
        "summary": "On-campus male hostel capacity exhausted; placed in external property with dedicated shuttle.",
        "cost_impact_inr": 39600.0,
        "people_affected": 18,
        "approved_by": "usr_director",
        "approved_at": "2026-10-31T00:30:00Z",
        "override_id": null
      }
    ],
    "total": 14,
    "page": 1,
    "page_size": 20
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/decisions/{id}`
- **Description**: Returns complete details of a specific decision card.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "dec_accom_041",
    "module": "accommodation",
    "decision_type": "EXTERNAL_PROPERTY_SPILLOVER",
    "title": "Placed IIT Bombay Contingent (18 pax) in Lakeview Hotel",
    "summary": "On-campus male hostel capacity exhausted; placed in external property with dedicated shuttle.",
    "why": "On-campus male capacity was fully exhausted. Lakeview Hotel provided 18 contiguous beds preserving contingent cohesion, while Central Residency only had 6 fragmented beds.",
    "hard_constraints_satisfied": [
      "Gender segregation (all-male placement verified)",
      "Zero unplaced participants in arrival wave"
    ],
    "soft_constraints_relaxed": [
      {
        "constraint": "On-campus housing preference",
        "reason": "Hostel capacity at 100% occupancy"
      }
    ],
    "alternatives_rejected": [
      {
        "option": "Split contingent across 3 on-campus hostels",
        "why": "Violates contingent cohesion constraint and separates minor leader"
      },
      {
        "option": "Central Residency placement",
        "why": "Insufficient contiguous capacity (only 6 beds available)"
      }
    ],
    "cost_impact_inr": 39600.0,
    "people_affected": 18,
    "approved_by": "usr_director",
    "approved_at": "2026-10-31T00:30:00Z",
    "override_id": null,
    "entity_refs": [
      { "type": "contingent", "id": "C01", "label": "IIT Bombay" },
      { "type": "external_property", "id": "EXT04", "label": "Lakeview Hotel" }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/decisions/{id}/why`
- **Description**: One-click explanation breakdown returning human-readable explanation and constraint resolution summary.
- **Response `200 OK`**:
```json
{
  "data": {
    "decision_id": "dec_accom_041",
    "title": "Placed IIT Bombay Contingent (18 pax) in Lakeview Hotel",
    "explanation": "On-campus male capacity was fully exhausted. Lakeview Hotel provided 18 contiguous beds preserving contingent cohesion, while Central Residency only had 6 fragmented beds.",
    "hard_constraints_satisfied": [
      "Gender segregation (all-male placement verified)",
      "Zero unplaced participants in arrival wave"
    ],
    "soft_constraints_relaxed": [
      {
        "constraint": "On-campus housing preference",
        "reason": "Hostel capacity at 100% occupancy"
      }
    ],
    "alternatives_rejected": [
      {
        "option": "Split contingent across 3 on-campus hostels",
        "why": "Violates contingent cohesion constraint and separates minor leader"
      }
    ],
    "approver": "usr_director",
    "timestamp": "2026-10-31T00:30:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/decisions`
- **Description**: Creates and persists a new decision card.
- **Request Body**:
```json
{
  "module": "schedule",
  "decision_type": "VENUE_RELOCATION",
  "title": "Relocated Coding Prelims to Computer Lab 2",
  "summary": "Audio interference from neighboring rock band finals required room swap.",
  "why": "Computer Lab 2 has sound dampening and 60 operational terminals.",
  "hard_constraints_satisfied": ["Minimum 40 terminals", "Accessibility compliance"],
  "soft_constraints_relaxed": [{"constraint": "Preferred Auditorium venue", "reason": "Acoustic bleed"}],
  "alternatives_rejected": [{"option": "Postpone event", "why": "Causes 3-hour downstream conflict"}],
  "cost_impact_inr": 0.0,
  "people_affected": 45,
  "override_id": null
}
```
- **Response `201 Created`**:
```json
{
  "data": {
    "id": "dec_sched_019",
    "status": "RECORDED"
  },
  "meta": {},
  "warnings": []
}
```
