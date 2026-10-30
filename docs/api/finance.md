# API Specification: `finance`

> Owner: `P2`  
> Base Path: `/api/v1/finance`  
> Status: `ACTIVE`

---

## 1. Overview
The **Finance & Commercial Operations** module oversees festival expenditures, external property invoices, vendor settlements, merchandise procurement costs, approved emergency disbursements, and budget compliance.

Key principles:
- **Finance Manager RBAC**: Access is strictly gated by the `FINANCE_MANAGER` and `FESTIVAL_DIRECTOR` roles.
- **Budget-Unset Mode**: In Aarohan 2026, `external_budget_inr = NULL` represents the unconstrained state where the Festival Director has not locked the budget limit. The engine operates transparently in budget-unset monitoring mode without inventing arbitrary budgets.
- **Cross-Service Accommodation Spend**: Dynamically pulls live external accommodation spend directly from `services.accommodation.public`.
- **Settlement Tracking & Disputes**: Manages vendor contracts, payment terms (minimum guarantee, 50% advance / balance actuals, per item sold), milestones, dispute logs, and payment deadlines.
- **Audited Financial Overrides**: Any budget override or emergency expenditure requires recorded reasons and authorization via `core.approvals` and `core.overrides`.

---

## 2. Endpoints

### 2.1 `GET /api/v1/finance/summary`
- **Description**: Returns overall budget gauge, committed spend, projected spend, variance, and explains budget-unset mode if `external_budget_inr` is null.
- **Response `200 OK`**:
```json
{
  "data": {
    "external_budget_inr": null,
    "budget_status": "BUDGET_UNSET",
    "budget_explanation": "External budget is currently UNSET by the Festival Director. System is calculating committed spend against unconstrained demand.",
    "total_spend_committed_inr": 2845000.0,
    "total_spend_projected_inr": 3450000.0,
    "cost_variance_inr": 605000.0,
    "breakdown": {
      "external_accommodation_inr": 1620000.0,
      "vendors_and_catering_inr": 780000.0,
      "merchandise_inr": 295000.0,
      "logistics_equipment_inr": 90000.0,
      "approved_emergency_inr": 60000.0
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
- **Description**: Pulls live external accommodation spending broken down by external property from `services.accommodation.public`.
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
        "rate_per_bed_night_inr": 1800.0,
        "total_spend_inr": 864000.0,
        "contract_status": "CONFIRMED",
        "payment_status": "ADVANCE_PAID"
      }
    ],
    "total_external_spend_inr": 1620000.0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/finance/vendor-settlements`
- **Description**: Tracks all vendor commercial settlements, payment terms, due dates, paid balances, and open billing disputes.
- **Response `200 OK`**:
```json
{
  "data": {
    "settlements": [
      {
        "id": "stl_01",
        "vendor_id": "VND01",
        "vendor_name": "Vendor A",
        "payment_terms": "minimum guarantee",
        "contract_total_inr": 280000.0,
        "advance_paid_inr": 100000.0,
        "balance_due_inr": 180000.0,
        "due_date": "2026-11-05",
        "status": "PENDING_VERIFICATION",
        "dispute": null
      },
      {
        "id": "stl_02",
        "vendor_id": "VND02",
        "vendor_name": "Vendor B",
        "payment_terms": "50% advance; balance actuals",
        "contract_total_inr": 195000.0,
        "advance_paid_inr": 80000.0,
        "balance_due_inr": 115000.0,
        "due_date": "2026-11-02",
        "status": "DISPUTED",
        "dispute": {
          "id": "dsp_01",
          "amount_inr": 18500.0,
          "reason": "Billed for 120 unauthorized extra lunch packs.",
          "opened_by": "Finance Manager",
          "opened_at": "2026-10-31T15:00:00Z"
        }
      }
    ],
    "total_payable_inr": 295000.0,
    "disputed_amount_inr": 18500.0,
    "overdue_count": 0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/finance/vendor-settlements/{id}/pay`
- **Description**: Records a vendor settlement payment via `ChangeService` (`finance.record_payment`).
- **Request Body**:
```json
{
  "amount_inr": 100000.0,
  "payment_reference": "NEFT_FEST_2026_9021",
  "notes": "50% advance payment disbursed per contract terms"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "settlement_id": "stl_01",
    "vendor_id": "VND01",
    "paid_amount_inr": 100000.0,
    "remaining_balance_inr": 80000.0,
    "status": "PARTIALLY_PAID"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/finance/vendor-settlements/{id}/dispute`
- **Description**: Opens a formal billing dispute for a vendor invoice via `ChangeService` (`finance.open_dispute`).
- **Request Body**:
```json
{
  "amount_inr": 18500.0,
  "reason": "Billed for 120 unauthorized extra lunch packs during storm delay without voucher."
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "settlement_id": "stl_02",
    "status": "DISPUTED",
    "disputed_amount_inr": 18500.0,
    "dispute_id": "dsp_01"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/finance/merchandise-costs`
- **Description**: Summarizes merchandise procurement costs, unit prices, quantities, and delivery status.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "item_name": "T-shirt",
        "unit_cost_inr": 190.0,
        "ordered_qty": 2850,
        "total_cost_inr": 541500.0,
        "supplier": "Aero Apparels",
        "status": "DELIVERED"
      }
    ],
    "total_merchandise_spend_inr": 831750.0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `GET /api/v1/finance/emergency-spend`
- **Description**: Log of all approved emergency expenditures with justifications and Director authorizations.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "emg_01",
        "description": "Backup Diesel Generator for Main Stage sound rig",
        "amount_inr": 35000.0,
        "category": "VENDOR_BACKUP",
        "approved_by": "Festival Director",
        "approved_at": "2026-10-31T06:15:00Z",
        "reason": "Grid transformer voltage fluctuation threat during Inauguration",
        "audit_link": "aud_emg_991"
      }
    ],
    "total_emergency_spend_inr": 35000.0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `POST /api/v1/finance/emergency-spend`
- **Description**: Proposes an emergency disbursement via `ChangeService` (`finance.emergency_spend`), requiring Director approval.
- **Request Body**:
```json
{
  "description": "Emergency commercial water tankers for campus kitchens",
  "amount_inr": 25000.0,
  "category": "VENDOR_BACKUP",
  "reason": "Municipal supply pipe pressure drop"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "PENDING_APPROVAL",
    "approval_id": "appr_emg_502",
    "amount_inr": 25000.0
  },
  "meta": {},
  "warnings": ["Requires Festival Director authorization."]
}
```

---

### 2.9 `GET /api/v1/finance/overrides-report`
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
        "delta_inr": 144000.0,
        "reason": "Rate hike accepted to secure 160 guaranteed beds on fest weekend.",
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

---

### 2.10 `POST /api/v1/finance/budget/set`
- **Description**: Sets the `external_budget_inr` assumption, locking the external budget limit (Festival Director only).
- **Request Body**:
```json
{
  "budget_inr": 3500000.0,
  "reason": "Executive board approved funding cap"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "external_budget_inr": 3500000.0,
    "budget_status": "BUDGET_SET",
    "updated_at": "2026-10-31T10:00:00Z"
  },
  "meta": {},
  "warnings": []
}
```
