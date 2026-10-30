# API Specification: `dashboard`

> Owner: `P1`  
> Base Path: `/api/v1/dashboard`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Central Operational Control Dashboard** provides the festival's unified real-time command centre.
It coordinates:
- **Module Metrics Aggregation (`/metrics`)**: Gathers and projects the state of all 32 modules from their respective `public.summary()` implementations. Metrics include:
  - Participants: total, arrived, checked-in, pending arrivals.
  - Accommodation: occupancy percentage, available beds, unplaced participants.
  - Schedule & Events: active sessions, open conflicts.
  - Logistics & Merchandise: equipment availability, merchandise stock on-hand and issued.
  - Food & Vendors: vendor operational status, food coverage gaps.
  - Staff & Ops: staff availability, open incidents, pending approvals, active overrides.
- **Short-TTL Invalidation Cache**: Metrics are cached for up to 15 seconds and automatically invalidated when domain mutation events are published on the bus (e.g. `*.applied`, `*.created`, `*.updated`).
- **Role-Aware Filtering**:
  - `VOLUNTEER` callers receive a sanitized operational view omitting financial figures, internal incidents, and director-only approvals.
  - Department Leads receive operational and department-specific data.
  - `FESTIVAL_DIRECTOR` and `AUDITOR` receive the complete overview.
- **Priority Attention Queue (`/attention`)**: Collects active risks across all registered modules via `iter_public_modules()`, deduplicates identical issues, and strictly ranks them by:
  $$\text{Score} = \text{Severity (1--4)} \times \text{Urgency (1--5)} \times \max(\text{People Affected}, 1)$$
  using `app.core.scoring`.
  Every alert provides an actionable direct route and/or API endpoint to resolve the problem.
- **Risk Heatmap (`/heatmap`)**: Multi-dimensional severity $\times$ time-to-impact matrix displaying people affected, resource criticality, uncertainty, and top contributing issues per cell.

---

## 2. Endpoints

### 2.1 `GET /api/v1/dashboard/metrics`
- **Description**: Returns consolidated KPI metrics across the entire festival, filtered by caller role.
- **Query Parameters**:
  - `bypass_cache` (bool, optional, default: false)
- **Response `200 OK`**:
```json
{
  "data": {
    "participants": {
      "total": 2836,
      "arrived": 1420,
      "checked_in": 1280,
      "pending_arrivals": 1416
    },
    "accommodation": {
      "occupancy_pct": 82.4,
      "available_beds": 312,
      "unplaced_participants": 48
    },
    "schedule": {
      "active_sessions": 14,
      "open_conflicts": 3
    },
    "logistics": {
      "equipment_available": 450,
      "equipment_in_transit": 12,
      "equipment_under_repair": 31
    },
    "merchandise": {
      "total_stock": 3500,
      "issued_count": 1280,
      "available_stock": 2220
    },
    "food": {
      "active_vendors": 6,
      "coverage_gaps": 2,
      "uncovered_meals": 180
    },
    "staff": {
      "core_team_active": 48,
      "volunteers_on_shift": 18,
      "peak_staffing_gap": 56
    },
    "governance": {
      "open_incidents": 2,
      "pending_approvals": 5,
      "active_overrides": 3
    },
    "cached_at": "2026-10-31T01:00:00Z",
    "is_cached": true
  },
  "meta": {
    "role": "FESTIVAL_DIRECTOR"
  },
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/dashboard/attention`
- **Description**: Returns deduplicated, prioritized attention queue ranked strictly by `core.scoring` ($\text{Severity} \times \text{Urgency} \times \text{People Affected}$).
- **Query Parameters**:
  - `limit` (int, default: 20)
  - `min_severity` (int, optional: 1--4)
  - `module` (string, optional: e.g. `accommodation`, `schedule`, `staff`, `logistics`)
- **Response `200 OK`**:
```json
{
  "data": {
    "attention_items": [
      {
        "id": "risk_unplaced_participants",
        "module": "accommodation",
        "kind": "UNPLACED_PARTICIPANTS",
        "title": "48 participants currently have no confirmed room placement",
        "severity": 4,
        "hours_to_impact": 2.0,
        "urgency": 4,
        "people_affected": 48,
        "score": 768.0,
        "resource_criticality": 4,
        "uncertainty": 0.05,
        "action": {
          "label": "Auto-Allocate Rooms",
          "route": "/accommodation/rooms",
          "api": "/api/v1/accommodation/allocate"
        },
        "explanation": "Arrival wave in 2 hours exceeds available on-campus male hostel beds."
      },
      {
        "id": "risk_staff_shortage",
        "module": "staff",
        "kind": "VOLUNTEER_SHORTAGE",
        "title": "Critical volunteer deficit: peak gap of 56 volunteers across 34.0h",
        "severity": 4,
        "hours_to_impact": 4.0,
        "urgency": 4,
        "people_affected": 56,
        "score": 896.0,
        "resource_criticality": 4,
        "uncertainty": 0.1,
        "action": {
          "label": "View Coverage Gaps",
          "route": "/staff/demand",
          "api": "/api/v1/staff/demand"
        },
        "explanation": "Event sessions require up to 74 simultaneous volunteers but peak shift coverage is 18."
      }
    ],
    "total_unresolved": 12
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/dashboard/heatmap`
- **Description**: Returns 2D risk heatmap cells organized by severity ($1\text{--}4$) and time-to-impact urgency ($1\text{--}5$), with people affected, uncertainty, resource criticality, and top contributors per cell.
- **Response `200 OK`**:
```json
{
  "data": {
    "matrix": [
      {
        "severity": 4,
        "urgency": 5,
        "urgency_label": "IMMEDIATE",
        "time_window": "<= 1 hour",
        "risk_count": 2,
        "people_affected": 94,
        "avg_uncertainty": 0.05,
        "max_criticality": 5,
        "is_critical_quadrant": true,
        "top_risks": [
          {
            "id": "risk_unconfirmed_accessibility",
            "title": "Wheelchair user arriving in 30m assigned to 2nd-floor non-accessible room",
            "module": "accommodation",
            "action_route": "/accommodation/rooms"
          }
        ]
      }
    ],
    "summary": {
      "critical_quadrant_risks": 3,
      "total_risks_mapped": 14
    }
  },
  "meta": {},
  "warnings": []
}
```
