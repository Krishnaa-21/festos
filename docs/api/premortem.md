# API Specification: `premortem`

> Owner: `P2`  
> Base Path: `/api/v1/premortem`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Pre-Mortem module provides proactive resilience stress-testing and time-travel simulation across the festival window (Oct 29 08:00 to Nov 01 22:00).
Key capabilities:
- **Hourly Timeline Scrubber**: Evaluates festival operational state hour-by-hour: bed occupancy & availability, food demand vs vendor availability, venue utilization, equipment demand, volunteer coverage, transport requirements, and calls each registered module's `public.risks(session, current_hour)` without modifying module code.
- **Disruption Generator**: Executes targeted disruptions (bus delay, hostel closure, vendor stop, equipment failure, venue unavailable, staff shortage, demand surge, transport interruption, late contingent) and seeded random multi-disruption runs in isolated scenario sandboxes using the impact engine.
- **Single Points of Failure (SPOF) Detection**: Identifies resources whose failure impacts large numbers of participants with zero operational alternatives.
- **Explainable Resilience Score**: Computes a weighted 0-100 resilience score across 8 domains (disruption resistance, SPOFs, accommodation, food, venues, equipment, volunteers, safety) with full component breakdown, accompanied by an explicit planning indicator disclaimer (see `docs/RESILIENCE_METHOD.md`).
- **Scenario History**: Archives pre-mortem simulation runs and mitigations for retrospective analysis.

---

## 2. Endpoints

### 2.1 `GET /api/v1/premortem/timeline`
- **Description**: Returns an hourly operational scrubber across the festival horizon. Computes occupancy, demand, capacities, and queries `public.risks(session, hour)` across all 32 modules for each discrete hour.
- **Query Parameters**:
  - `start_time` (ISO-8601 string, optional, default: `2026-10-29T08:00:00Z`)
  - `end_time` (ISO-8601 string, optional, default: `2026-11-01T22:00:00Z`)
  - `step_hours` (int, default: 1)
- **Response `200 OK`**:
```json
{
  "data": {
    "start_time": "2026-10-29T08:00:00Z",
    "end_time": "2026-11-01T22:00:00Z",
    "total_hours": 87,
    "timeline": [
      {
        "timestamp": "2026-10-30T14:00:00Z",
        "accommodation": {
          "total_beds": 1450,
          "occupied_beds": 1280,
          "available_beds": 170,
          "occupancy_rate_pct": 88.28
        },
        "food": {
          "total_demand": 1400,
          "vendor_capacity": 1650,
          "coverage_deficit": 0,
          "active_vendors": 12
        },
        "venues": {
          "active_events": 8,
          "peak_venue_utilization_pct": 85.0,
          "congested_venues": ["V01"]
        },
        "equipment": {
          "units_demanded": 54,
          "units_available": 60,
          "shortage": 0
        },
        "volunteers": {
          "volunteers_required": 48,
          "volunteers_scheduled": 52,
          "coverage_gap": 0
        },
        "transport": {
          "shuttles_in_transit": 4,
          "passengers_en_route": 120,
          "active_routes": 3
        },
        "critical_risks": [
          {
            "module": "accommodation",
            "code": "ACC_NEAR_CAPACITY",
            "severity": 3,
            "people_affected": 170,
            "description": "Hostel Block A is at 94% capacity with pending arrivals."
          }
        ],
        "hourly_risk_count": 1,
        "max_severity": 3
      }
    ],
    "peak_stress_hour": "2026-10-30T18:00:00Z"
  },
  "meta": {
    "simulated_window": "FESTIVAL_HORIZON",
    "risk_modules_queried": 32
  },
  "warnings": []
}
```

---

### 2.2 `POST /api/v1/premortem/disruptions/run`
- **Description**: Runs a targeted single-disruption simulation in an isolated scenario sandbox using the impact engine. Re-runs allocation and scheduling to calculate blast radius, affected people, single points of failure, and preventive suggestions.
- **Request Body**:
```json
{
  "disruption_type": "HOSTEL_CLOSURE",
  "target_entity_id": "HOSTEL_C",
  "parameters": {
    "effective_time": "2026-10-30T12:00:00Z",
    "duration_hours": 24,
    "closure_reason": "Electrical plumbing failure"
  }
}
```
Supported `disruption_type` values:
- `BUS_DELAY`
- `HOSTEL_CLOSURE`
- `VENDOR_STOP`
- `EQUIPMENT_FAILURE`
- `VENUE_UNAVAILABLE`
- `STAFF_SHORTAGE`
- `DEMAND_SURGE`
- `TRANSPORT_INTERRUPTION`
- `LATE_CONTINGENT`

- **Response `200 OK`**:
```json
{
  "data": {
    "scenario_id": "scen_prem_88129",
    "disruption_type": "HOSTEL_CLOSURE",
    "target_entity": "HOSTEL_C",
    "people_affected": 140,
    "events_affected": 0,
    "critical_failures": [
      "140 participants displaced into unplaced queue",
      "Contingent C03 split across external properties"
    ],
    "is_spof": true,
    "preventive_actions": [
      {
        "action": "CONTRACT_STANDBY_EXTERNAL_BEDS",
        "description": "Block 60 backup rooms at Lakeview Inn prior to Day 2",
        "cost_inr": 45000.0,
        "reduction_in_affected": 120
      }
    ],
    "post_disruption_resilience_score": 64.2
  },
  "meta": {
    "sandbox_db": "scenarios/scen_prem_88129.db"
  },
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/premortem/disruptions/multi-run`
- **Description**: Executes seeded multi-disruption Monte Carlo / combinatorial stress test in scenario sandboxes. Uses explicit random seeds (`random.Random(seed)`) to ensure perfect reproducibility.
- **Request Body**:
```json
{
  "seed": 42,
  "disruption_count": 3,
  "intensity": "HIGH",
  "disruption_types": ["BUS_DELAY", "VENDOR_STOP", "EQUIPMENT_FAILURE"]
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "seed": 42,
    "disruptions_applied": [
      { "type": "BUS_DELAY", "entity": "SHUTTLE_ROUTE_02", "delay_minutes": 180 },
      { "type": "VENDOR_STOP", "entity": "VEND_JAIN_01", "meal_slot": "LUNCH_DAY2" },
      { "type": "EQUIPMENT_FAILURE", "entity": "PROJ_AUDITORIUM_01" }
    ],
    "total_unique_people_affected": 268,
    "composite_resilience_score": 58.7,
    "spofs_exposed": ["VEND_JAIN_01", "SHUTTLE_ROUTE_02"],
    "scenario_id": "scen_prem_seed_42"
  },
  "meta": {
    "reproducible": true
  },
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/premortem/resilience`
- **Description**: Evaluates current operational resilience using the explainable weighted formula documented in `docs/RESILIENCE_METHOD.md`.
- **Response `200 OK`**:
```json
{
  "data": {
    "festival_resilience_score": 78.4,
    "max_score": 100.0,
    "rating": "MODERATE_RESILIENCE",
    "disclaimer": "Planning indicator for identifying operational vulnerabilities; not a probability of success.",
    "methodology_reference": "docs/RESILIENCE_METHOD.md",
    "components": {
      "disruption_resistance": {
        "score": 75.0,
        "weight": 0.20,
        "weighted_score": 15.0,
        "detail": "8.5% population affected under stress tests"
      },
      "critical_dependencies_spofs": {
        "score": 65.0,
        "weight": 0.15,
        "weighted_score": 9.75,
        "detail": "2 unmitigated Single Points of Failure found"
      },
      "accommodation_buffer": {
        "score": 82.0,
        "weight": 0.15,
        "weighted_score": 12.30,
        "detail": "170 spare beds over peak requirement"
      },
      "vendor_redundancy": {
        "score": 80.0,
        "weight": 0.10,
        "weighted_score": 8.00,
        "detail": "85% meal slots have >= 2 vendor backups"
      },
      "venue_redundancy": {
        "score": 85.0,
        "weight": 0.10,
        "weighted_score": 8.50,
        "detail": "Peak venue load 85%"
      },
      "equipment_availability": {
        "score": 70.0,
        "weight": 0.10,
        "weighted_score": 7.00,
        "detail": "12% standby units in depot"
      },
      "staff_volunteer_coverage": {
        "score": 88.0,
        "weight": 0.10,
        "weighted_score": 8.80,
        "detail": "92% volunteer shift slots filled"
      },
      "safety_coverage": {
        "score": 90.0,
        "weight": 0.10,
        "weighted_score": 9.00,
        "detail": "90% minor duty-of-care contacts verified"
      }
    },
    "vulnerabilities": [
      {
        "rank": 1,
        "domain": "Accommodation",
        "description": "Hostel C single-point-of-failure if power disruption occurs",
        "severity": 4,
        "mitigation": "Contract 60 standby external beds"
      },
      {
        "rank": 2,
        "domain": "Food Operations",
        "description": "Amphitheatre has zero Jain lunch vendor backup",
        "severity": 3,
        "mitigation": "Add Jain meal box delivery from Central Mess"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/premortem/spofs`
- **Description**: Returns all detected Single Points of Failure (resources whose loss halts operations for $\ge 50$ people or stops events with no alternative).
- **Response `200 OK`**:
```json
{
  "data": {
    "total_spofs": 3,
    "spofs": [
      {
        "entity_type": "HOSTEL",
        "entity_id": "HOSTEL_C",
        "name": "Hostel Block C",
        "people_at_risk": 140,
        "alternative_available": false,
        "impact_summary": "Loss leaves 140 participants with no on-campus beds",
        "preventive_recommendation": "Contract standby capacity at Lakeview Inn"
      },
      {
        "entity_type": "VENDOR",
        "entity_id": "VEND_03",
        "name": "Shree Jain Caterers",
        "people_at_risk": 85,
        "alternative_available": false,
        "impact_summary": "Sole provider of Jain diet meals for South Zone",
        "preventive_recommendation": "Designate Central Mess as backup Jain provider"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/premortem/scenarios`
- **Description**: Returns history of pre-mortem simulation runs.
- **Response `200 OK`**:
```json
{
  "data": {
    "scenarios": [
      {
        "scenario_id": "scen_prem_88129",
        "created_at": "2026-10-31T04:00:00Z",
        "disruption_type": "HOSTEL_CLOSURE",
        "people_affected": 140,
        "resilience_score": 64.2
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
