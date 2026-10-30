# API Specification: `overrides`

> Owner: `P3`  
> Base Path: `/api/v1/overrides`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Override register tracks all operational constraint relaxations and policy bypasses (e.g. bed capacity limits, contingent cohesion, proximity, or accessibility rules). In accordance with FestOS product principles, hard constraints may only be relaxed with an explicit, recorded reason by an authorized approver (Festival Director). All overrides are immutably logged and accessible for real-time monitoring and post-fest audits.

---

## 2. Endpoints

### 2.1 `GET /api/v1/overrides`
- **Description**: Query the override register with filtering, pagination, and sorting.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `entity_type` (string, optional)
  - `constraint_code` (string, optional)
  - `risk_level` (string, optional: `LOW`, `HIGH`, `CRITICAL`)
  - `status` (string, optional: `ACTIVE`, `REVOKED`, `EXPIRED`)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "ovr_11223344",
        "entity_type": "room",
        "entity_id": "RM_H1_204",
        "constraint_code": "CAPACITY_LIMIT",
        "reason": "Emergency overflow cot added for contingent leader",
        "approved_by": "Festival Director",
        "approved_at": "2026-10-30T12:45:00Z",
        "risk_level": "HIGH",
        "status": "ACTIVE"
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

### 2.2 `POST /api/v1/overrides`
- **Description**: Manually record an operational override directly into the register. Mandatory reason required.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Request Body**:
```json
{
  "entity_type": "event_session",
  "entity_id": "ses_debate_r2",
  "constraint_code": "VENUE_DOUBLE_BOOKING",
  "reason": "Host auditorium divided with sound-insulating partition for simultaneous heats",
  "risk_level": "HIGH"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "ovr_99887766",
    "entity_type": "event_session",
    "entity_id": "ses_debate_r2",
    "constraint_code": "VENUE_DOUBLE_BOOKING",
    "reason": "Host auditorium divided with sound-insulating partition for simultaneous heats",
    "approved_by": "Festival Director",
    "approved_at": "2026-10-30T13:30:00Z",
    "risk_level": "HIGH",
    "status": "ACTIVE"
  },
  "meta": {},
  "warnings": ["Override logged in override register and immutable audit log."]
}
```

---

### 2.3 `GET /api/v1/overrides/{id}`
- **Description**: Retrieve specific override details.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "ovr_99887766",
    "entity_type": "event_session",
    "entity_id": "ses_debate_r2",
    "constraint_code": "VENUE_DOUBLE_BOOKING",
    "reason": "Host auditorium divided with sound-insulating partition for simultaneous heats",
    "approved_by": "Festival Director",
    "approved_at": "2026-10-30T13:30:00Z",
    "risk_level": "HIGH",
    "status": "ACTIVE"
  },
  "meta": {},
  "warnings": []
}
```
