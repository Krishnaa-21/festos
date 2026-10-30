# API Specification: `vendors`

> Owner: `P2`  
> Base Path: `/api/v1/vendors`  
> Status: `ACTIVE`

---

## 1. Overview
The **Vendors & Catering Operations** module manages commercial contracts, meal-slot capacities, compliance certifications, menu-label verification, and emergency vendor shutdowns.

Key principles:
- **14 Canonical Vendors**: Ingested from `vendors.csv` with profiles, menus, declared dietary options, operating hours, baseline capacities, and payment terms.
- **Dynamic Capacity & Expiry**: Certificates are evaluated against festival dates (Oct 30 - Nov 2, 2026). If a certificate expires mid-festival (e.g. Oct 31), vendor capacity is valid until the expiry timestamp and drops out from that moment onwards (never dropped for the whole festival).
- **Menu-Label Verification**: Keyword classifier checks menu items against declared dietary categories. Flags mismatches (e.g., `VND09` Jain thali with no Jain declared; `VND11` vegan bowls with non-vegetarian/halal declared) for human verification—never auto-fixed. Categories claimed without confirmation show as `UNVERIFIED`.
- **Emergency Shutdown Response**: Implements the 10-step analysis (`vendor_shutdown_analysis`):
  1. Affected locations
  2. Meal slots
  3. Lost capacity
  4. Dietary gaps
  5. Ranked replacements (dietary match, certificate validity, operating hours, spare capacity, location, rate)
  6. Backup capacity check (flags if backup vendor cannot absorb the load)
  7. Cost change calculation (cost delta INR)
  8. Actionable recommendations
  9. Notification drafts per audience
  10. State update executed through `ChangeService` (`vendors.shutdown`).

---

## 2. Endpoints

### 2.1 `GET /api/v1/vendors`
- **Description**: Returns all vendors with compliance status, hours, declared options, per-meal-slot/location capacity, and payment terms.
- **Query Params**: `status` (`ACTIVE`, `SUSPENDED`, `SHUT_DOWN`), `dietary_option`, `compliance_status` (`VALID_THROUGHOUT`, `EXPIRES_DURING_FESTIVAL`, `EXPIRED`).
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "VND01",
        "name": "Vendor A",
        "status": "ACTIVE",
        "menu_description": "North Indian",
        "dietary_options": "vegetarian",
        "declared_categories": ["vegetarian"],
        "unverified_categories": [],
        "hours": "07:00-23:00",
        "capacity": 264,
        "hygiene_certificate_expiry": "2026-10-31",
        "compliance_status": "EXPIRES_DURING_FESTIVAL",
        "payment_terms": "minimum guarantee",
        "base_rate_per_meal_inr": 180.0,
        "contact_phone": "+91-9876543201",
        "assigned_slots_count": 4
      }
    ],
    "total": 14
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/vendors/{id}`
- **Description**: Detailed profile of a vendor including menu items, assignments to locations and meal slots, rates, and compliance breakdown.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "VND09",
    "name": "Vendor I",
    "status": "ACTIVE",
    "menu_description": "Jain thali",
    "dietary_options": "vegetarian",
    "declared_categories": ["vegetarian"],
    "unverified_categories": ["jain"],
    "hours": "07:00-23:00",
    "capacity": 369,
    "hygiene_certificate_expiry": "2027-10-29",
    "compliance_status": "VALID_THROUGHOUT",
    "payment_terms": "per item sold",
    "base_rate_per_meal_inr": 190.0,
    "assignments": [
      {
        "id": "vna_09_01",
        "meal_slot_id": "msl_lunch_20261031",
        "meal_slot_name": "LUNCH",
        "date": "2026-10-31",
        "venue_id": "V04",
        "location_name": "Food Court B",
        "allocated_capacity": 369,
        "rate_per_meal_inr": 190.0,
        "status": "SCHEDULED"
      }
    ],
    "compliance_flags": [
      {
        "code": "MENU_LABEL_MISMATCH",
        "message": "Menu item 'Jain thali' implies Jain preparation, but Jain is not declared in dietary options.",
        "severity": "HIGH",
        "requires_confirmation": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/vendors/{id}/shutdown-impact`
- **Description**: Evaluates the 10-step emergency shutdown analysis from a specific timestamp (`from_time`).
- **Request Body**:
```json
{
  "from_time": "2026-10-31T12:00:00Z",
  "reason": "Health inspector order: bacterial contamination alert"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "vendor_id": "VND01",
    "vendor_name": "Vendor A",
    "from_time": "2026-10-31T12:00:00Z",
    "affected_locations": ["Food Court A", "Dining Hall 1"],
    "affected_meal_slots": ["LUNCH", "DINNER"],
    "lost_capacity": 264,
    "dietary_gaps": [
      {
        "category": "vegetarian",
        "deficit": 264,
        "is_zero_coverage": false
      }
    ],
    "ranked_replacements": [
      {
        "vendor_id": "VND03",
        "vendor_name": "Vendor C",
        "spare_capacity": 361,
        "dietary_match": "EXACT (vegetarian)",
        "compliance_status": "VALID_THROUGHOUT",
        "operating_hours": "07:00-23:00",
        "can_absorb_load": true,
        "rate_per_meal_inr": 195.0,
        "cost_delta_inr": 3960.0,
        "rank": 1,
        "rationale": "Valid certificate, exact dietary match, sufficient spare capacity (+97 cushion)."
      }
    ],
    "backup_capacity_check": {
      "total_replacement_capacity": 361,
      "required_capacity": 264,
      "can_absorb_load": true,
      "warning": null
    },
    "cost_change_inr": 3960.0,
    "recommendation": "Assign Vendor C (VND03) to replace Vendor A (VND01) across Food Court A for Lunch and Dinner.",
    "notification_drafts": [
      {
        "audience": "contingent_leaders",
        "channel": "SMS",
        "subject": "Dining Update: Food Court A Catering",
        "body": "Notice: Vendor A is temporarily offline. Meals are transferred to Vendor C at Food Court A."
      },
      {
        "audience": "volunteers",
        "channel": "APP",
        "subject": "OPERATIONAL: Vendor A Shutdown",
        "body": "Direct vegetarian lunch/dinner participants from Vendor A stalls to Vendor C counters."
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/vendors/{id}/shutdown`
- **Description**: Executes emergency vendor shutdown via `ChangeService` (`vendors.shutdown`), updates status to `SHUT_DOWN`, reassigns slots to approved replacement, and stages notification drafts.
- **Headers**: `Idempotency-Key` (required)
- **Request Body**:
```json
{
  "from_time": "2026-10-31T12:00:00Z",
  "reason": "Severe hygiene infraction detected during audit",
  "replacement_vendor_id": "VND03",
  "dispatch_notifications": true
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "APPLIED",
    "vendor_id": "VND01",
    "new_status": "SHUT_DOWN",
    "replacement_assigned": "VND03",
    "slots_reassigned": 2,
    "change_set_id": "cs_vnd_shut_401",
    "drafts_created": 3
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/vendors/compliance`
- **Description**: Returns compliance breakdown across all 14 vendors, certificate statuses, and menu-label mismatch flags.
- **Response `200 OK`**:
```json
{
  "data": {
    "vendors": [
      {
        "id": "VND05",
        "name": "Vendor E",
        "certificate_expiry": "2026-09-29",
        "validity_period": "EXPIRED",
        "capacity_allowed": 0
      },
      {
        "id": "VND01",
        "name": "Vendor A",
        "certificate_expiry": "2026-10-31",
        "validity_period": "EXPIRES_DURING_FESTIVAL",
        "capacity_allowed_before_expiry": 264,
        "capacity_allowed_after_expiry": 0
      }
    ],
    "menu_mismatches": [
      {
        "vendor_id": "VND09",
        "menu_item": "Jain thali",
        "declared_options": ["vegetarian"],
        "mismatch_type": "MISSING_DECLARED_CATEGORY",
        "flag": "Jain preparation implied but not declared"
      },
      {
        "vendor_id": "VND11",
        "menu_item": "Vegan bowls",
        "declared_options": ["non-vegetarian", "halal"],
        "mismatch_type": "CONFLICTING_DECLARATION",
        "flag": "Vegan item marketed with non-vegetarian/halal declaration"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/vendors/reports/{report_name}`
- **Description**: Streams downloadable CSV reports for `vendor_coverage.csv` and `vendor_compliance.csv`.
- **Response `200 OK`**: `text/csv`.
