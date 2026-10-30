# API Specification: `imports`

> Owner: `P2`  
> Base Path: `/api/v1/imports`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `imports` module provides the ingestion pipeline turning raw external CSV packs into validated, staged, and canonically promoted data without silently dropping uncertainty.

Flow:
1. `POST /api/v1/imports` receives a raw CSV file multipart upload.
2. The immutable raw rows are stored byte-for-byte in `raw_record`.
3. Column mapping is applied via `data/mapping/<file>.yaml`.
4. Validation rules detect structural anomalies, invalid intervals, minor safety thresholds, and cross-file discrepancies. Invalid rows are isolated into `quarantine_row` with clear reason codes.
5. `POST /api/v1/imports/{id}/promote` invokes the `imports.promote` ChangeService handler to atomically promote staged rows into canonical entities with audit logging and rollback support.
6. Re-imports are idempotent based on content hash. Dry-run previews are supported.

---

## 2. Endpoints

### 2.1 `POST /api/v1/imports`
- **Description**: Upload a raw CSV file for ingestion, validation, and staging.
- **Headers**:
  - `Idempotency-Key` (string, optional)
- **Form Data**:
  - `file`: UploadFile (CSV file)
  - `sheet_name`: string (optional, e.g. `participants`, `registrations`, `contingents`, `events`, `venues`, `core_team`, `hostels`, `external_stays`, `inventory_logistics`, `inventory_merch`, `vendors`)
  - `dry_run`: boolean (default: `false`)
- **Response `200 OK`**:
```json
{
  "data": {
    "batch_id": "imp_9a8b7c6d",
    "filename": "participants.csv",
    "sheet_name": "participants",
    "content_hash": "a1b2c3d4e5f6...",
    "total_rows": 2836,
    "imported_rows": 2833,
    "quarantined_rows": 3,
    "status": "COMPLETED",
    "dry_run": false,
    "imported_at": "2026-10-30T13:30:00Z"
  },
  "meta": {
    "execution_time_ms": 142
  },
  "warnings": [
    "3 rows quarantined due to invalid arrival/departure intervals"
  ]
}
```

---

### 2.2 `GET /api/v1/imports`
- **Description**: List all import batches and ingestion history.
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `status` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "imp_9a8b7c6d",
        "filename": "participants.csv",
        "sheet_name": "participants",
        "content_hash": "a1b2c3d4e5f6...",
        "total_rows": 2836,
        "imported_rows": 2833,
        "quarantined_rows": 3,
        "status": "COMPLETED",
        "imported_at": "2026-10-30T13:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/imports/{id}`
- **Description**: Fetch summary details of a specific import batch.
- **Path Parameters**:
  - `id`: string (e.g. `imp_9a8b7c6d`)
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "imp_9a8b7c6d",
    "filename": "participants.csv",
    "sheet_name": "participants",
    "content_hash": "a1b2c3d4e5f6...",
    "total_rows": 2836,
    "imported_rows": 2833,
    "quarantined_rows": 3,
    "status": "COMPLETED",
    "imported_at": "2026-10-30T13:30:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/imports/{id}/issues`
- **Description**: List quarantined rows and validation issues for a batch.
- **Path Parameters**:
  - `id`: string (batch id)
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "qrn_001",
        "batch_id": "imp_9a8b7c6d",
        "reason": "INVALID_ARRIVAL_DEPARTURE_INTERVAL",
        "severity": 4,
        "raw_payload": {
          "participant_id": "P0037",
          "name": "Meera Bose",
          "arrival_datetime": "2026-11-02 02:00",
          "departure_datetime": "2026-10-31 20:00"
        },
        "created_at": "2026-10-30T13:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/imports/{id}/promote`
- **Description**: Promote staged records from an import batch to canonical operational tables through ChangeService handler `imports.promote`.
- **Headers**:
  - `Idempotency-Key` (UUID, mandatory for mutating change)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Approved canonical promotion following initial verification",
  "dry_run": false,
  "payload": {
    "include_quarantine": false
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_promote_12345",
    "status": "APPLIED",
    "violations": [],
    "audit_event_ids": ["aud_78910"],
    "impact": {
      "promoted_entities": 2833,
      "quarantined_retained": 3
    },
    "recommendations": [],
    "warnings": []
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/data-quality`
- **Description**: Comprehensive data-quality report across all imported sheets. Lists issues per file/field/severity, counts of UNKNOWN per field with operational impact, and the reconciliation summary shell.
- **Response `200 OK`**:
```json
{
  "data": {
    "summary": {
      "raw_participant_count": 2836,
      "narrative_expected_count": 2400,
      "contingent_declared_total": 2842,
      "difference_raw_vs_narrative": 436,
      "difference_raw_vs_declared": -6,
      "total_quarantined": 3,
      "total_issues": 18
    },
    "unknown_fields": [
      {
        "entity": "participant",
        "field": "gender",
        "unknown_count": 1262,
        "operational_impact": "Cannot automatically allocate to gender-segregated hostel blocks without manual review or gender-neutral assignment"
      },
      {
        "entity": "participant",
        "field": "diet",
        "unknown_count": 394,
        "operational_impact": "Default meal catering cannot guarantee dietary clearance or allergen compliance"
      }
    ],
    "issues": [
      {
        "file": "participants.csv",
        "field": "arrival_datetime",
        "severity": 4,
        "code": "INVALID_ARRIVAL_DEPARTURE_INTERVAL",
        "message": "3 participants have arrival scheduled after departure",
        "count": 3
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
