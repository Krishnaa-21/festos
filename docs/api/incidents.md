# API Specification: `incidents`

> Owner: `P2`  
> Base Path: `/api/v1/incidents`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The incidents module logs operational disruptions, tracks severities (1 LOW to 4 CRITICAL), links related entities (hostels, venues, equipment, vendors), dispatches remediation workflows, and provides an audited MTTR resolution log.

---

## 2. Endpoints

### 2.1 `GET /api/v1/incidents`
- **Description**: List all operational incidents, filtered by status, severity, or domain.
- **Query Parameters**:
  - `status` (string, optional: `OPEN`, `IN_PROGRESS`, `RESOLVED`)
  - `severity` (int, optional: 1-4)
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "inc_001",
        "title": "Hostel C Power Disruption",
        "severity": 4,
        "status": "OPEN",
        "reported_by": "Campus Facility Manager",
        "entity_refs": [{"type": "hostel", "id": "Hostel C", "label": "Hostel Block C"}],
        "created_at": "2026-10-30T10:00:00Z"
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

### 2.2 `POST /api/v1/incidents`
- **Description**: Log a new festival incident via ChangeService (`incident.create`).
- **Headers**:
  - `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "reason": "Immediate incident declaration",
  "payload": {
    "title": "Audio Equipment Failure at Main Auditorium",
    "severity": 3,
    "entity_type": "venue",
    "entity_id": "VEN01",
    "details": "Microphone mixer channel failure before debate preliminary"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_inc_9901",
    "status": "APPLIED",
    "incident_id": "inc_8820"
  },
  "meta": {},
  "warnings": []
}
```
