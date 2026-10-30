# API Specification: `finance`

> Owner: `P2`  
> Base Path: `/api/v1/finance`  
> Status: `CONTRACT_DRAFT`

---

## 1. Overview
The **Finance & Commercials** module tracks budget commitments, expenditure, external property invoices, vendor settlements, merchandise procurement, and emergency disbursements.
Key principles:
- **Budget-Unset Mode**: In FestOS context, `external_budget_inr = NULL` represents the unconstrained state where the Festival Director has not locked the budget limit. The engine clearly displays this mode without crashing or inventing arbitrary budgets.
- **Audit & Override Reporting**: Every financial override or budget breach surfaces in the overrides register with reason and authorization logs.

---

## 2. Endpoints

### 2.1 `GET /api/v1/finance/summary`
- **Description**: Returns budget gauge metrics, committed spend, projected spend, and explains the budget-unset state if `external_budget_inr` is null.
- **Response `200 OK`**:
```json
{
  "data": {
    "external_budget_inr": null,
    "budget_status": "BUDGET_UNSET",
    "budget_explanation": "External accommodation budget is currently UNSET by the Festival Director. Engine is calculating committed spend against unconstrained demand. Festival Director authorization required to set ceiling.",
    "total_spend_committed_inr": 2845000,
    "total_spend_projected_inr": 3450000,
    "breakdown": {
      "external_accommodation_inr": 1620000,
      "vendors_and_catering_inr": 780000,
      "merchandise_inr": 295000,
      "logistics_equipment_inr": 90000,
      "approved_emergency_inr": 60000
    }
  },
  "meta": {},
  "warnings": [
    "external_budget_inr is NULL: Operating in budget-unset monitoring mode."
  ]
}
```

---

### 2.2 `GET /api/v1/finance/accommodation-spend`
- **Description**: External accommodation spend broken down by property.
- **Response `200 OK`**:
```json
{
  "data": {
    "properties": [
      {
        "property_id": "prop_01",
        "name": "Lemon Tree Hotel",
        "capacity_beds": 180,
        "booked_beds": 160,
        "nights": 3,
        "rate_per_bed_night_inr": 1800,
        "total_spend_inr": 864000,
        "contract_status": "CONFIRMED",
        "payment_status": "ADVANCE_PAID"
      },
      {
        "property_id": "prop_02",
        "name": "Ginger Indore",
        "capacity_beds": 120,
        "booked_beds": 110,
        "nights": 3,
        "rate_per_bed_night_inr": 1400,
        "total_spend_inr": 462000,
        "contract_status": "CONFIRMED",
        "payment_status": "PARTIAL"
      },
      {
        "property_id": "prop_03",
        "name": "Royal Palace Residency",
        "capacity_beds": 90,
        "booked_beds": 75,
        "nights": 3,
        "rate_per_bed_night_inr": 1300,
        "total_spend_inr": 292500,
        "contract_status": "PENDING_FINAL_ROOMING",
        "payment_status": "PENDING"
      }
    ],
    "total_external_spend_inr": 1618500
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/finance/vendor-settlements`
- **Description**: Vendor commercial settlements, balances due, payment milestones, and billing disputes.
- **Response `200 OK`**:
```json
{
  "data": {
    "settlements": [
      {
        "vendor_id": "vnd_01",
        "vendor_name": "Annapurna Caterers",
        "contract_total_inr": 280000,
        "advance_paid_inr": 100000,
        "balance_due_inr": 180000,
        "due_date": "2026-11-05",
        "status": "PENDING_VERIFICATION",
        "dispute": null
      },
      {
        "vendor_id": "vnd_02",
        "vendor_name": "Spice Junction",
        "contract_total_inr": 195000,
        "advance_paid_inr": 80000,
        "balance_due_inr": 115000,
        "due_date": "2026-11-02",
        "status": "DISPUTED",
        "dispute": {
          "id": "dsp_01",
          "amount_inr": 18500,
          "reason": "Billed for 120 extra lunch packs during Oct 31 storm delay without authorization token.",
          "opened_by": "Finance Manager",
          "opened_at": "2026-10-31T15:00:00Z"
        }
      }
    ],
    "total_payable_inr": 295000,
    "disputed_amount_inr": 18500
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/finance/merchandise-costs`
- **Description**: Summary of merchandise procurement costs, unit prices, and quantities.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "item_name": "T-shirt",
        "unit_cost_inr": 190,
        "ordered_qty": 2850,
        "total_cost_inr": 541500,
        "supplier": "Aero Apparels",
        "status": "DELIVERED"
      },
      {
        "item_name": "Accreditation ID & Lanyard",
        "unit_cost_inr": 35,
        "ordered_qty": 3000,
        "total_cost_inr": 105000,
        "supplier": "PrintFast Media",
        "status": "DELIVERED"
      },
      {
        "item_name": "Festival Tote Bag",
        "unit_cost_inr": 65,
        "ordered_qty": 2850,
        "total_cost_inr": 185250,
        "supplier": "EcoBags India",
        "status": "DELIVERED"
      }
    ],
    "total_merchandise_spend_inr": 831750
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/finance/emergency-spend`
- **Description**: Log of approved emergency expenditures with justification and director approvals.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "emg_01",
        "description": "Backup Diesel Generator for Main Stage sound rig",
        "amount_inr": 35000,
        "approved_by": "Festival Director",
        "approved_at": "2026-10-31T06:15:00Z",
        "reason": "Grid transformer voltage fluctuation threat during Inauguration",
        "audit_link": "aud_emg_991"
      },
      {
        "id": "emg_02",
        "description": "Heavy-duty waterproof tarpaulins for Amphitheatre equipment",
        "amount_inr": 25000,
        "approved_by": "Festival Director",
        "approved_at": "2026-10-31T12:30:00Z",
        "reason": "Sudden weather bulletin predicting rain showers",
        "audit_link": "aud_emg_992"
      }
    ],
    "total_emergency_spend_inr": 60000
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/finance/overrides-report`
- **Description**: Audit report of all financial and constraint overrides across all festival modules.
- **Response `200 OK`**:
```json
{
  "data": {
    "overrides": [
      {
        "id": "ovr_fin_01",
        "category": "BUDGET_OVERRIDE",
        "target_entity": "Lemon Tree Hotel (prop_01)",
        "original_value": "₹1500 / bed-night",
        "overridden_value": "₹1800 / bed-night",
        "delta_inr": 144000,
        "reason": "Rate hike accepted to secure 160 guaranteed beds on fest weekend due to citywide hotel rush.",
        "authorized_by": "Festival Director",
        "authorized_at": "2026-10-28T14:20:00Z",
        "audit_event_id": "aud_ovr_3120"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
