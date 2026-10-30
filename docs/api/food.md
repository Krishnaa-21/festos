# API Specification: `food`

> Owner: `P2`  
> Base Path: `/api/v1/food`  
> Status: `ACTIVE`

---

## 1. Overview
The **Food & Dietary Operations** module calculates meal demand from the on-site participant headcount timeline, models vendor capacity per meal slot and location, evaluates dietary coverage, and flags compliance risks.

Key principles:
- **On-Site Headcount Demand**: Demand is derived from the arrival and departure timelines of participants on campus during each meal slot.
- **`UNKNOWN` Dietary Stays Separate**: Blank or missing dietary preferences are never assumed vegetarian; they remain strictly in the `UNKNOWN` category and are represented as a demand range (`min_demand` = confirmed, `max_demand` = confirmed + unknown).
- **8 Dietary Categories**: `vegetarian`, `non-vegetarian`, `vegan`, `jain`, `halal`, `gluten-free`, `nut-allergy`, `other` (plus `unknown`).
- **Zero-Coverage Alerting**: Any dietary category with zero compliant vendors triggers a critical alert (e.g. Jain, gluten-free, nut allergy).
- **Dynamic Mid-Festival Expiry**: Capacity drops out from the moment a vendor's hygiene certificate expires, directly affecting per-slot coverage after the expiry time.

---

## 2. Endpoints

### 2.1 `GET /api/v1/food/coverage`
- **Description**: Returns the comprehensive dietary coverage matrix per meal slot, venue, and dietary category, including capacity, demand, gaps, and zero-coverage alerts.
- **Query Params**: `date` (`YYYY-MM-DD`), `meal_slot` (`BREAKFAST`, `LUNCH`, `SNACKS`, `DINNER`, `LATE_NIGHT`), `venue_id`.
- **Response `200 OK`**:
```json
{
  "data": {
    "date": "2026-10-31",
    "categories": [
      "vegetarian",
      "non-vegetarian",
      "vegan",
      "jain",
      "halal",
      "gluten-free",
      "nut-allergy",
      "other",
      "unknown"
    ],
    "meal_slots": ["BREAKFAST", "LUNCH", "SNACKS", "DINNER", "LATE_NIGHT"],
    "summary": {
      "on_site_headcount": 1930,
      "valid_aggregate_capacity": 1590,
      "aggregate_shortfall": 340,
      "zero_coverage_categories": ["jain", "gluten-free", "nut-allergy"],
      "unknown_dietary_headcount": 394
    },
    "matrix": [
      {
        "meal_slot": "LUNCH",
        "date": "2026-10-31",
        "category": "vegetarian",
        "demand_confirmed": 439,
        "demand_max_with_unknown": 833,
        "valid_capacity": 1590,
        "deficit": 0,
        "is_zero_coverage": false,
        "active_vendors": ["VND01", "VND02", "VND03"]
      },
      {
        "meal_slot": "LUNCH",
        "date": "2026-10-31",
        "category": "jain",
        "demand_confirmed": 380,
        "demand_max_with_unknown": 774,
        "valid_capacity": 0,
        "deficit": 380,
        "is_zero_coverage": true,
        "active_vendors": []
      }
    ],
    "critical_alerts": [
      {
        "code": "ZERO_COMPLIANT_VENDORS",
        "category": "jain",
        "severity": "CRITICAL",
        "message": "Zero compliant vendors available for Jain dietary requirements. 380 participants unserved."
      },
      {
        "code": "ZERO_COMPLIANT_VENDORS",
        "category": "gluten-free",
        "severity": "CRITICAL",
        "message": "Zero compliant vendors available for Gluten-Free dietary requirements. 387 participants unserved."
      }
    ]
  },
  "meta": {},
  "warnings": [
    "Peak headcount on Oct 31 (1,930) exceeds valid vendor capacity (1,590) by 340 meals."
  ]
}
```

---

### 2.2 `GET /api/v1/food/compliance`
- **Description**: Returns menu-label mismatch flags and unverified dietary claims detected across vendor menus.
- **Response `200 OK`**:
```json
{
  "data": {
    "flags": [
      {
        "id": "flg_mismatch_09",
        "vendor_id": "VND09",
        "vendor_name": "Vendor I",
        "flag_type": "MENU_LABEL_MISMATCH",
        "menu_keyword": "Jain thali",
        "declared_options": ["vegetarian"],
        "severity": "HIGH",
        "status": "UNVERIFIED",
        "message": "Vendor I menu item 'Jain thali' implies Jain preparation, but Jain is not in declared dietary options.",
        "requires_human_confirmation": true
      },
      {
        "id": "flg_mismatch_11",
        "vendor_id": "VND11",
        "vendor_name": "Vendor K",
        "flag_type": "MENU_LABEL_MISMATCH",
        "menu_keyword": "Vegan bowls",
        "declared_options": ["non-vegetarian", "halal"],
        "severity": "HIGH",
        "status": "UNVERIFIED",
        "message": "Vendor K advertises 'Vegan bowls' but declared options are non-vegetarian and halal. Certificate also expired.",
        "requires_human_confirmation": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/food/slots`
- **Description**: Lists all festival meal slots with timing, dates, and assigned capacities.
- **Response `200 OK`**:
```json
{
  "data": {
    "slots": [
      {
        "id": "msl_breakfast_20261031",
        "name": "BREAKFAST",
        "date": "2026-10-31",
        "start_time": "07:30",
        "end_time": "10:00",
        "assigned_vendors_count": 6
      },
      {
        "id": "msl_lunch_20261031",
        "name": "LUNCH",
        "date": "2026-10-31",
        "start_time": "12:00",
        "end_time": "15:00",
        "assigned_vendors_count": 10
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
