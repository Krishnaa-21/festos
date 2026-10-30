# API Specification: `food`

> Owner: `P2`  
> Base Path: `/api/v1/food`  
> Status: `CONTRACT_DRAFT`

---

## 1. Overview
The **Food & Dietary Operations** module guarantees dietary coverage and food safety compliance across all fest venues and meal slots.
Key principles:
- **Zero-Coverage Alerting**: Vendor capacity must cover every dietary category (Veg, Non-Veg, Jain, Vegan, Gluten-Free) at each venue during each meal slot (Breakfast, Lunch, Snacks, Dinner, Late-Night). Zero-coverage cells require immediate operational intervention.
- **Menu vs Declaration Consistency**: Automatic detection of mismatches between vendor self-declared dietary labels and actual menu ingredients (e.g. garlic/onion items labeled as Jain).
- **Proactive Compliance**: Hygiene certificate tracking with proactive expiration warnings before fest days.

---

## 2. Endpoints

### 2.1 `GET /api/v1/food/coverage`
- **Description**: Returns the 3D dietary coverage matrix (`category` x `meal_slot` x `venue`) with capacity, expected demand, deficit, and zero-coverage indicators.
- **Response `200 OK`**:
```json
{
  "data": {
    "categories": ["VEG", "NON_VEG", "JAIN", "VEGAN", "GLUTEN_FREE"],
    "meal_slots": ["BREAKFAST", "LUNCH", "SNACKS", "DINNER", "LATE_NIGHT"],
    "venues": ["V01", "V02", "V03", "V04", "V07"],
    "matrix": [
      {
        "category": "JAIN",
        "meal_slot": "LUNCH",
        "venue_id": "V04",
        "venue_name": "Amphitheatre",
        "capacity": 0,
        "demand": 45,
        "deficit": 45,
        "is_zero_coverage": true,
        "assigned_vendors": []
      },
      {
        "category": "VEG",
        "meal_slot": "LUNCH",
        "venue_id": "V04",
        "venue_name": "Amphitheatre",
        "capacity": 350,
        "demand": 280,
        "deficit": 0,
        "is_zero_coverage": false,
        "assigned_vendors": ["vnd_01", "vnd_03"]
      }
    ],
    "summary": {
      "total_slots": 125,
      "covered_slots": 118,
      "zero_coverage_count": 7,
      "critical_gaps": [
        {
          "category": "JAIN",
          "meal_slot": "LUNCH",
          "venue_name": "Amphitheatre",
          "affected_count": 45
        }
      ]
    }
  },
  "meta": {},
  "warnings": [
    "7 zero-coverage cells detected. Attendees in Amphitheatre have no Jain lunch vendor."
  ]
}
```

---

### 2.2 `GET /api/v1/food/compliance`
- **Description**: List food safety and dietary compliance issues, menu-label mismatch flags, and expiring certifications.
- **Response `200 OK`**:
```json
{
  "data": {
    "flags": [
      {
        "id": "flg_jain_mismatch_01",
        "vendor_id": "vnd_02",
        "vendor_name": "Spice Junction",
        "flag_type": "MENU_LABEL_MISMATCH",
        "severity": "HIGH",
        "message": "Declared 'Jain-Friendly' but item 'Paneer Butter Masala' lists onion gravy in ingredient spec.",
        "item_name": "Paneer Butter Masala",
        "detected_at": "2026-10-30T09:00:00Z",
        "status": "OPEN",
        "recommended_action": "Flag menu item or restrict vendor from Jain meal slot"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
