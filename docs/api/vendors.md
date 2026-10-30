# API Specification: `vendors`

> Owner: `P2`  
> Base Path: `/api/v1/vendors`  
> Status: `CONTRACT_DRAFT`

---

## 1. Overview
The **Vendors & Catering** module manages commercial contracts, venue-slot assignments, menu pricing, compliance certifications, and emergency vendor shutdowns.
Key principles:
- **Emergency Vendor Shutdown**: When health, hygiene, or operational breach occurs, the system calculates lost meal capacity, finds ranked substitute vendors, estimates cost delta, and queues notification drafts for Director approval.
- **Commercial Rates**: Transparent record of minimum guarantee rates, per-meal cost, and payment terms.

---

## 2. Endpoints

### 2.1 `GET /api/v1/vendors`
- **Description**: List all vendors with current operating status, compliance expiry, menu overview, and capacities.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "vnd_01",
        "name": "Annapurna Caterers",
        "status": "ACTIVE",
        "dietary_options": "VEG, JAIN",
        "menu_description": "North Indian Thali, Jain Thali, Evening Snacks",
        "capacity": 450,
        "hours": "07:00-23:00",
        "hygiene_certificate_expiry": "2026-11-15",
        "days_to_expiry": 16,
        "payment_terms": "MINIMUM_GUARANTEE_PLUS_ACTUALS",
        "base_rate_per_meal_inr": 180,
        "contact_phone": "+91-9876543210"
      },
      {
        "id": "vnd_02",
        "name": "Spice Junction",
        "status": "ACTIVE",
        "dietary_options": "VEG, NON_VEG",
        "menu_description": "Biryani, Curry, Rolls",
        "capacity": 300,
        "hours": "11:00-02:00",
        "hygiene_certificate_expiry": "2026-10-31",
        "days_to_expiry": 1,
        "payment_terms": "FIXED_PER_MEAL",
        "base_rate_per_meal_inr": 220,
        "contact_phone": "+91-9812345678"
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
- **Description**: Detailed profile of vendor including active assignments, rates, and past performance.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "vnd_01",
    "name": "Annapurna Caterers",
    "status": "ACTIVE",
    "capacity": 450,
    "assignments": [
      {
        "id": "vna_01",
        "date": "2026-10-31",
        "meal_slot": "LUNCH",
        "venue_id": "V04",
        "venue_name": "Amphitheatre",
        "expected_meals": 400,
        "agreed_rate_inr": 180
      }
    ],
    "commercials": {
      "minimum_guarantee_inr": 150000,
      "base_rate_per_meal_inr": 180,
      "advance_paid_inr": 50000
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/vendors/{id}/shutdown-impact`
- **Description**: Simulates the downstream impact of shutting down a vendor.
- **Response `200 OK`**:
```json
{
  "data": {
    "vendor_id": "vnd_02",
    "vendor_name": "Spice Junction",
    "lost_capacity": 300,
    "affected_slots": [
      {
        "date": "2026-10-31",
        "meal_slot": "LUNCH",
        "venue_name": "Food Court",
        "meals_deficit": 300
      }
    ],
    "ranked_replacements": [
      {
        "vendor_id": "vnd_05",
        "vendor_name": "Royal Feast Caterers",
        "available_capacity": 350,
        "dietary_match": "EXACT (VEG, NON_VEG)",
        "proximity_score": 0.95,
        "rate_per_meal_inr": 240,
        "cost_delta_inr": 6000,
        "rank": 1,
        "rationale": "Directly adjacent to Food Court with verified 350-meal reserve capacity."
      },
      {
        "vendor_id": "vnd_08",
        "vendor_name": "Express Meals",
        "available_capacity": 250,
        "dietary_match": "PARTIAL (VEG only)",
        "proximity_score": 0.70,
        "rate_per_meal_inr": 210,
        "cost_delta_inr": -3000,
        "rank": 2,
        "rationale": "Lower cost but requires second vendor for non-veg deficit."
      }
    ],
    "cost_delta_inr": 6000,
    "notification_drafts": [
      {
        "recipient_group": "AFFECTED_PARTICIPANTS",
        "channel": "SMS",
        "template": "Dining Notice: Spice Junction stall at Food Court is offline. Lunch served at Royal Feast counter.",
        "requires_director_approval": false
      },
      {
        "recipient_group": "FOOD_OPS_LEADS",
        "channel": "APP",
        "template": "CRITICAL: Spice Junction shutdown enacted. Royal Feast assigned to Food Court.",
        "requires_director_approval": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/vendors/{id}/shutdown`
- **Description**: Executes emergency vendor shutdown via `ChangeService`, reassigning slots and queueing notifications.
- **Headers**: `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "reason": "Severe hygiene violation reported by campus health inspector",
  "replacement_vendor_id": "vnd_05",
  "dispatch_notifications": true
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "APPLIED",
    "vendor_id": "vnd_02",
    "new_status": "SHUTDOWN",
    "replacement_assigned": "vnd_05",
    "notifications_dispatched": 2,
    "change_set_id": "cs_vnd_shut_102"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/vendors/compliance`
- **Description**: Returns all vendor compliance certifications, days to expiry, and audit status.
- **Response `200 OK`**:
```json
{
  "data": {
    "certifications": [
      {
        "vendor_id": "vnd_02",
        "vendor_name": "Spice Junction",
        "certificate_type": "FSSAI Food Hygiene",
        "certificate_number": "FSSAI-MP-2024-9982",
        "valid_until": "2026-10-31",
        "days_left": 1,
        "status": "CRITICAL_EXPIRING",
        "audit_pass": true
      },
      {
        "vendor_id": "vnd_07",
        "vendor_name": "Campus QuickBite",
        "certificate_type": "Municipal Health NOC",
        "certificate_number": "IND-MNC-2025-110",
        "valid_until": "2026-11-01",
        "days_left": 2,
        "status": "WARNING_EXPIRING",
        "audit_pass": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
