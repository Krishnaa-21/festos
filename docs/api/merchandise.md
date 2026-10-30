# API Specification: `merchandise`

> Owner: `P1`  
> Base Path: `/api/v1/merchandise`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Merchandise Management** module controls the festival swag and credential lifecycle.
Key responsibilities:
- **Catalog & Sizing**: Tracks inventory by item and size (`T-shirt` sizes S, M, L, XL, XXL; non-sized items `ID card`, `lanyard`, `tote`, `winner medal`, `special badge`).
- **Canonical Entitlements**: Entitlements are computed per **CANONICAL** participant record (merged duplicate participants cannot claim duplicate merch).
- **Entitlement Policy**:
  - Per-head items (`T-shirt`, `ID card`, `lanyard`, `tote`, `special badge`): default 1 per verified participant.
  - Winner medals: event-result-based, not general per-head distribution.
  - Policy is explicitly editable and exposed with rationale.
  - UNKNOWN sizes are flagged for desk verification.
- **Transactional & Idempotent Issuance**:
  - `POST /api/v1/merchandise/issue` executes inside a transactional lock (enforced by DB unique constraint `uq_merch_claim_participant_item`).
  - Writes the `merch_claim` record and the ledger movement `ISSUE` atomically.
  - Re-attempting an issue yields `409 ALREADY_ISSUED` containing original timestamp, counter location, and staff member details.
  - Voiding an issue requires recorded reason and `FESTIVAL_DIRECTOR` or `MERCHANDISE_MANAGER` approval.
  - Volunteer-role responses filter out sensitive personal fields (exposing only minimal verification info).
- **QR Scanning & Offline Sync**:
  - Cryptographic HMAC-signed tokens generated with `QR_SECRET`.
  - Batch printable SVG/sheet generation for accreditation cards.
  - `POST /api/v1/merchandise/scan` verifies token and processes issue.
  - `POST /api/v1/merchandise/sync` accepts batch operations with `client_op_id` idempotency for offline desk recovery.

---

## 2. Endpoints

### 2.1 `GET /api/v1/merchandise/catalog`
- **Description**: List merchandise catalog items, sizes, on-hand counts, reservations, and available units.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "mch_tshirt_xl",
        "name": "T-shirt",
        "size": "XL",
        "on_hand": 713,
        "reserved": 29,
        "available": 684,
        "is_per_head": true
      },
      {
        "id": "mch_medal_na",
        "name": "winner medal",
        "size": "NA",
        "on_hand": 2269,
        "reserved": 16,
        "available": 2253,
        "is_per_head": false
      }
    ],
    "total": 10
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/merchandise/policy`
- **Description**: Returns the current merchandise entitlement policies and size-wise demand breakdown.
- **Response `200 OK`**:
```json
{
  "data": {
    "policy_name": "Standard Fest Entitlement Baseline",
    "is_editable": true,
    "rules": [
      {"item": "T-shirt", "entitlement": "1 per canonical participant", "per_head": true},
      {"item": "ID card", "entitlement": "1 per canonical participant", "per_head": true},
      {"item": "lanyard", "entitlement": "1 per canonical participant", "per_head": true},
      {"item": "tote", "entitlement": "1 per canonical participant", "per_head": true},
      {"item": "winner medal", "entitlement": "Event result allocation only", "per_head": false}
    ],
    "size_breakdown": {
      "S": {"demand": 435, "stock": 449, "net": 14},
      "M": {"demand": 850, "stock": 115, "net": -735, "shortage_alert": true},
      "L": {"demand": 620, "stock": 234, "net": -386, "shortage_alert": true},
      "XL": {"demand": 680, "stock": 713, "net": 33},
      "XXL": {"demand": 110, "stock": 136, "net": 26},
      "UNKNOWN": {"count": 141, "flag": "NEEDS_SIZE_COLLECTION"}
    }
  },
  "meta": {
    "note": "Demand is policy-dependent based on canonical participant headcount."
  },
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/merchandise/issue`
- **Description**: Issue an item to a participant. Idempotent and atomic.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
  - `X-Actor-Role` (string, e.g. `VOLUNTEER` | `MERCHANDISE_MANAGER`)
  - `X-Actor-Id` (string, e.g. `usr_vol_01`)
- **Request Body**:
```json
{
  "participant_id": "p_00192",
  "item_id": "mch_tshirt_l",
  "counter_id": "counter_desk_north",
  "size_override": null,
  "reason": "Registration desk kit handover"
}
```
- **Response `200 OK` (First Success)**:
```json
{
  "data": {
    "claim_id": "clm_88192a",
    "canonical_participant_id": "p_00192",
    "item_id": "mch_tshirt_l",
    "item_name": "T-shirt",
    "size": "L",
    "issued_at": "2026-10-31T08:35:10Z",
    "issued_by": "usr_vol_01",
    "counter_id": "counter_desk_north",
    "status": "ISSUED"
  },
  "meta": {},
  "warnings": []
}
```
- **Response `409 Conflict` (Already Issued)**:
```json
{
  "error": {
    "code": "ALREADY_ISSUED",
    "message": "Item T-shirt already issued to this participant",
    "details": {
      "claim_id": "clm_88192a",
      "canonical_participant_id": "p_00192",
      "claimed_at": "2026-10-31T08:35:10Z",
      "issued_by": "usr_vol_01",
      "counter_id": "counter_desk_north"
    },
    "request_id": "req_88192"
  }
}
```

---

### 2.4 `POST /api/v1/merchandise/void`
- **Description**: Void an existing merch claim. Requires justification and approval.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "claim_id": "clm_88192a",
  "reason": "Participant swapped defective zipper tote for fresh unit",
  "return_to_awaiting_inspection": true
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "claim_id": "clm_88192a",
    "status": "VOIDED",
    "voided_at": "2026-10-31T09:12:00Z",
    "inventory_movement_type": "RETURN",
    "item_status": "AWAITING_RETURN"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/merchandise/qr/{participant_id}`
- **Description**: Returns signed HMAC QR token data and SVG format for accreditation badges.
- **Response `200 OK`**:
```json
{
  "data": {
    "participant_id": "p_00192",
    "token": "hmac_v1_p00192_8fbc29a3",
    "svg": "<svg xmlns='http://www.w3.org/2000/svg' ...>...</svg>",
    "entitlements": ["T-shirt", "ID card", "lanyard", "tote"]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `POST /api/v1/merchandise/scan`
- **Description**: Validates HMAC signed QR token and displays/issues merchandise entitlement.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "token": "hmac_v1_p00192_8fbc29a3",
  "counter_id": "counter_desk_north",
  "auto_issue_items": ["mch_id_card", "mch_lanyard"]
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "valid": true,
    "canonical_participant_id": "p_00192",
    "name": "Arjun Sharma",
    "contingent": "IIT Bombay",
    "entitlements": [
      {"item": "ID card", "status": "ISSUED", "claim_id": "clm_01"},
      {"item": "lanyard", "status": "ISSUED", "claim_id": "clm_02"},
      {"item": "T-shirt", "status": "PENDING", "size": "L"}
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/merchandise/sync`
- **Description**: Bulk offline sync for scan operations conducted when network drops.
- **Request Body**:
```json
{
  "operations": [
    {
      "client_op_id": "op_off_001",
      "participant_id": "p_00192",
      "item_id": "mch_tshirt_l",
      "timestamp": "2026-10-31T08:30:00Z",
      "counter_id": "counter_desk_north"
    }
  ]
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "synced_count": 1,
    "failed_count": 0,
    "results": [
      {
        "client_op_id": "op_off_001",
        "status": "APPLIED",
        "claim_id": "clm_88192a"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
