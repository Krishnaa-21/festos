# API Specification: `logistics`

> Owner: `P1`  
> Base Path: `/api/v1/logistics`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The **Logistics & Equipment** module manages time- and location-aware physical inventory across the festival campus.
It enforces a pure double-entry inventory ledger where:
- Physical stock is never confused with available stock.
- Quantities are never directly overwritten; all changes are immutable ledger movements (`RECEIVE`, `RESERVE`, `RELEASE`, `TRANSFER_OUT`, `TRANSFER_IN`, `ISSUE`, `RETURN`, `DAMAGE`, `SEND_REPAIR`, `REPAIR_DONE`, `ADJUST`).
- In-transit stock counts at **neither** endpoint until an explicit transfer completion step (`TRANSFER_IN`).
- Returned equipment/merchandise sits in `awaiting_return` until inspected.
- Projections compute:
  $$\text{available} = \text{on\_hand} - \text{reserved} - \text{damaged} - \text{under\_repair} - \text{awaiting\_return}$$
- Equipment allocations to event sessions factor in travel times from the travel matrix plus transfer/loading durations.
- Equipment failure analysis determines dependent sessions (via Schedule public contract), alternative units, and transfer feasibility.
- The 'camera' case (none in good condition although three are needed) and tables 'needs check' surface as reconciliation flags rather than unverified shortages.

---

## 2. Endpoints

### 2.1 `GET /api/v1/logistics/items`
- **Description**: List inventory items (equipment & logistics) with projected stock buckets.
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `kind` (string, optional: `equipment` | `merch` | `all`)
  - `q` (string, optional: search by name or code)
  - `location_id` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "itm_cam_01",
        "name": "camera",
        "code": "L13-1",
        "kind": "equipment",
        "condition": "UNDER_REPAIR",
        "location_id": "loc_reg_desk",
        "location_name": "Registration Desk",
        "on_hand": 7,
        "reserved": 0,
        "in_transit": 0,
        "damaged": 0,
        "under_repair": 7,
        "awaiting_return": 0,
        "available": 0,
        "low_stock_threshold": 3
      }
    ],
    "total": 73,
    "page": 1,
    "page_size": 20,
    "total_pages": 4
  },
  "meta": {
    "timestamp": "2026-10-31T09:00:00Z"
  },
  "warnings": []
}
```

---

### 2.2 `POST /api/v1/logistics/movements`
- **Description**: Record an inventory movement in the immutable ledger via `ChangeService` (`logistics.record_movement`).
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Damaged cable found during morning inspection",
  "payload": {
    "item_id": "itm_mic_01",
    "from_location_id": "loc_reg_desk",
    "to_location_id": null,
    "quantity": 2,
    "movement_type": "DAMAGE",
    "reference_id": "inc_4421"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_mov_99812",
    "status": "APPLIED",
    "violations": [],
    "audit_event_ids": ["aud_77123"],
    "data": {
      "movement_id": "mvt_00129",
      "item_id": "itm_mic_01",
      "movement_type": "DAMAGE",
      "quantity": 2,
      "updated_projection": {
        "on_hand": 30,
        "damaged": 2,
        "available": 28
      }
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/logistics/transfers`
- **Description**: Initiate an equipment transfer between locations (`TRANSFER_OUT`). Stock in transit counts at neither origin nor destination.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "payload": {
    "item_id": "itm_spk_01",
    "from_location_id": "loc_store_a",
    "to_location_id": "loc_main_stage",
    "quantity": 4,
    "eta": "2026-10-31T11:30:00Z",
    "vehicle": "Van 1",
    "reason": "Transfer for afternoon band performance"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "transfer_id": "trf_0081",
    "item_id": "itm_spk_01",
    "from_location_id": "loc_store_a",
    "to_location_id": "loc_main_stage",
    "quantity": 4,
    "status": "IN_TRANSIT",
    "eta": "2026-10-31T11:30:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `POST /api/v1/logistics/transfers/{id}/complete`
- **Description**: Explicit completion step for a transfer (`TRANSFER_IN`). Stock is added to destination `on_hand`.
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Response `200 OK`**:
```json
{
  "data": {
    "transfer_id": "trf_0081",
    "status": "COMPLETED",
    "completed_at": "2026-10-31T11:28:44Z",
    "destination_location_id": "loc_main_stage",
    "quantity": 4
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `GET /api/v1/logistics/equipment/find`
- **Description**: Search equipment availability for an event session and time window.
- **Query Parameters**:
  - `item_name` (string, required: e.g. "projector" or "camera")
  - `venue_id` (string, required: e.g. "V01")
  - `start_at` (ISO datetime, required)
  - `end_at` (ISO datetime, required)
  - `quantity_needed` (int, default: 1 from assumption `equipment_default_quantity`)
- **Response `200 OK`**:
```json
{
  "data": {
    "item_name": "projector",
    "venue_id": "V01",
    "quantity_needed": 1,
    "available_on_site": [
      {
        "item_id": "itm_proj_03",
        "location_id": "loc_main_stage",
        "available_units": 20
      }
    ],
    "transfer_needed": [
      {
        "item_id": "itm_proj_01",
        "source_location_id": "loc_store_a",
        "available_units": 15,
        "travel_time_min": 15,
        "transfer_duration_min": 15,
        "feasible": true,
        "latest_departure": "2026-10-31T09:30:00Z"
      }
    ],
    "shortage": 0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/logistics/equipment/{id}/failure-analysis`
- **Description**: Analyzes the impact of equipment failure or damage on scheduled sessions.
- **Response `200 OK`**:
```json
{
  "data": {
    "item_id": "itm_mic_01",
    "item_name": "mic",
    "dependent_sessions": [
      {
        "session_id": "ses_0012",
        "event_id": "EV04",
        "event_name": "Western Solo Vocals",
        "venue_id": "V04",
        "start_at": "2026-10-31T10:00:00Z",
        "end_at": "2026-10-31T11:00:00Z"
      }
    ],
    "alternative_units": [
      {
        "item_id": "itm_mic_02",
        "location": "Store Room A",
        "available": 16,
        "transfer_time_min": 15,
        "feasible": true
      }
    ],
    "reconciliation_flags": []
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.7 `POST /api/v1/logistics/stocktake`
- **Description**: Record stocktake discrepancy adjustment (`ADJUST` movement with mandatory reason).
- **Headers**:
  - `Idempotency-Key` (UUID, required)
- **Request Body**:
```json
{
  "payload": {
    "item_id": "itm_chair_01",
    "location_id": "loc_store_a",
    "counted_quantity": 25,
    "current_on_hand": 29,
    "delta": -4,
    "reason": "Physical count revealed 4 broken chairs removed to scrapyard"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "APPLIED",
    "item_id": "itm_chair_01",
    "delta": -4,
    "new_on_hand": 25,
    "reason": "Physical count revealed 4 broken chairs removed to scrapyard"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `GET /api/v1/logistics/ledger/balance`
- **Description**: Verification check proving movements balance across the entire festival inventory.
- **Response `200 OK`**:
```json
{
  "data": {
    "consistent": true,
    "total_movements": 240,
    "total_inflow": 1420,
    "total_outflow": 1420,
    "discrepancies": []
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.9 `GET /api/v1/logistics/reconciliation-flags`
- **Description**: Returns equipment inconsistencies that must surface as reconciliation flags rather than confirmed shortages.
- **Response `200 OK`**:
```json
{
  "data": {
    "flags": [
      {
        "code": "CAMERA_ALL_UNDER_REPAIR",
        "item": "camera",
        "needed": 3,
        "available_good": 0,
        "total_under_repair": 31,
        "severity": "HIGH",
        "message": "All 31 cameras across 4 locations are logged as 'under repair'; 3 needed for Media Coverage."
      },
      {
        "code": "TABLES_NEEDS_CHECK",
        "item": "table",
        "location": "Sports Complex",
        "quantity": 42,
        "condition": "needs check",
        "severity": "MEDIUM",
        "message": "42 tables in Sports Complex flagged 'needs check'; physical condition unverified before morning session."
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
