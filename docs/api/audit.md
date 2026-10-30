# API Specification: `audit`

> Owner: `P3`  
> Base Path: `/api/v1/audit`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Audit module provides an append-only, tamper-evident cryptographic log of all mutations and security actions across FestOS. Every mutation records action, previous state, new state, user, role, timestamp, reason, approval ID, related incident/change ID, and a SHA-256 hash linked to the previous audit event (`prev_hash`). Direct SQL `UPDATE` and `DELETE` operations on `audit_event` are prohibited at the application layer and via database triggers.

---

## 2. Endpoints

### 2.1 `GET /api/v1/audit/events`
- **Description**: Query the immutable audit event log with filtering, pagination, and sorting. Contact, medical, and sensitive details in before/after snapshots are masked according to the requester's role.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Query Parameters**:
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
  - `entity_type` (string, optional)
  - `entity_id` (string, optional)
  - `actor_id` (string, optional)
  - `action` (string, optional)
  - `from_time` (ISO 8601 string, optional)
  - `to_time` (ISO 8601 string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "aud_01a2b3c4d5e6",
        "actor_id": "usr_dir_01",
        "actor_name": "Festival Director",
        "actor_role": "FESTIVAL_DIRECTOR",
        "action": "accommodation.assign_room",
        "entity_type": "room_assignment",
        "entity_id": "ra_101",
        "before_state": {
          "status": "VACANT",
          "bed_id": "B12"
        },
        "after_state": {
          "status": "OCCUPIED",
          "bed_id": "B12",
          "participant_id": "P10023"
        },
        "change_set_id": "cs_9876543210ab",
        "reason": "Allocated as per Contingent A cohesion plan",
        "status": "SUCCESS",
        "prev_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "current_hash": "7d793037a0760186574b0282f2f435e7090a6e4d66e8476dec76508001f725f2",
        "timestamp": "2026-10-30T13:20:00Z"
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

### 2.2 `GET /api/v1/audit/timeline/{entity_type}/{entity_id}`
- **Description**: Retrieve chronological change timeline for a specific entity.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK`**:
```json
{
  "data": {
    "entity_type": "participant",
    "entity_id": "P10023",
    "timeline": [
      {
        "id": "aud_01a2b3c4d5e6",
        "action": "participants.import",
        "actor_name": "System Seeder",
        "actor_role": "SYSTEM",
        "timestamp": "2026-10-30T12:00:00Z",
        "summary": "Initial participant record created",
        "diff": {
          "status": {"before": null, "after": "EXPECTED"}
        }
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/audit/verify`
- **Description**: Cryptographically verify the hash chain of all audit events from genesis to latest record. Detects any offline data tampering.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK` (Chain Valid)**:
```json
{
  "data": {
    "valid": true,
    "verified_count": 142,
    "genesis_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "latest_hash": "7d793037a0760186574b0282f2f435e7090a6e4d66e8476dec76508001f725f2",
    "broken_event_id": null
  },
  "meta": {},
  "warnings": []
}
```
- **Response `200 OK` (Tampering Detected)**:
```json
{
  "data": {
    "valid": false,
    "verified_count": 48,
    "broken_event_id": "aud_01a2b3c4d5e6",
    "message": "Hash chain divergence detected at event aud_01a2b3c4d5e6"
  },
  "meta": {},
  "warnings": ["CRITICAL: Database integrity violation detected in audit log!"]
}
```

---

### 2.4 `GET /api/v1/audit/export/csv`
- **Description**: Export filtered audit records as a CSV stream. All sensitive fields are strictly masked according to the exporting user's role and export permissions.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK`**:
- `Content-Type: text/csv`
```csv
id,timestamp,action,entity_type,entity_id,actor_name,actor_role,reason,prev_hash,current_hash
aud_01a2b3c4d5e6,2026-10-30T13:20:00Z,accommodation.assign_room,room_assignment,ra_101,Festival Director,FESTIVAL_DIRECTOR,Allocated as per plan,e3b0...,7d79...
```
