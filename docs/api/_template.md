# API Specification: `<module>`

> Owner: `[P1 | P2 | P3]`  
> Base Path: `/api/v1/<module>`  
> Status: `DRAFT | REVIEW | IMPLEMENTED`

---

## 1. Overview
Summary of module responsibility and key operations.

---

## 2. Endpoints

### 2.1 `GET /api/v1/<module>`
- **Description**: List entities with pagination and filtering.
- **Headers**:
  - `Authorization: Bearer <jwt>` (optional if auth disabled)
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `q` (string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20,
    "total_pages": 0
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `POST /api/v1/<module>`
- **Description**: Create or mutate an entity via ChangeService.
- **Headers**:
  - `Idempotency-Key` (UUID, required for mutating operations)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Initial operational allocation",
  "dry_run": false,
  "payload": {}
}
```
- **Response `200 OK` (Applied)**:
```json
{
  "data": {
    "change_set_id": "cs_1234567890",
    "status": "APPLIED",
    "violations": [],
    "audit_event_ids": ["aud_123456"],
    "impact": null,
    "recommendations": [],
    "warnings": []
  },
  "meta": {},
  "warnings": []
}
```
- **Response `202 Accepted` (Pending Approval)**:
```json
{
  "data": {
    "change_set_id": "cs_1234567890",
    "status": "PENDING_APPROVAL",
    "violations": [],
    "warnings": ["High-risk override requires Festival Director sign-off"]
  },
  "meta": {},
  "warnings": []
}
```
- **Response `409 Conflict` (Version Conflict)**:
```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "Entity version mismatch",
    "details": null,
    "request_id": "req_123"
  }
}
```
- **Response `422 Unprocessable Entity` (Constraint Violation)**:
```json
{
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Hard constraint violation",
    "details": [
      {
        "code": "CAPACITY_EXCEEDED",
        "severity": 4,
        "hard": true,
        "message": "Assigned beds exceed room capacity"
      }
    ],
    "request_id": "req_123"
  }
}
```
