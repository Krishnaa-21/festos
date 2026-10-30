# API Specification: `notifications`

> Owner: `P2`  
> Base Path: `/api/v1/notifications`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The notifications module manages operational broadcast drafts, role-targeted notices, dispatch queues, and critical festival alert notifications. All high-urgency notifications are routed through approvals before broadcast dispatch.

---

## 2. Endpoints

### 2.1 `GET /api/v1/notifications/drafts`
- **Description**: List active notification drafts with target roles, delivery channels, and approval status.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Query Parameters**:
  - `status` (string, optional: `DRAFT`, `PENDING_APPROVAL`, `DISPATCHED`, `REJECTED`)
  - `channel` (string, optional: `SMS`, `EMAIL`, `IN_APP`, `PUSH`)
  - `page` (int, default: 1)
  - `page_size` (int, default: 20)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "notif_001",
        "title": "Severe Weather Venue Relocation Notice",
        "message": "Outdoor sessions relocated to Sports Complex Hall B effective 14:00.",
        "target_group": "AFFECTED_PARTICIPANTS",
        "channel": "PUSH",
        "status": "DISPATCHED",
        "created_at": "2026-10-30T13:15:00Z"
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

### 2.2 `POST /api/v1/notifications/drafts`
- **Description**: Draft a new operational broadcast notification via ChangeService (`notification.draft`).
- **Headers**:
  - `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "reason": "Emergency schedule shift communication",
  "payload": {
    "title": "Bus Departure Delay Notice",
    "message": "Route 4 shuttle departure delayed by 20 minutes.",
    "target_group": "CAMPUS_RESIDENTS",
    "channel": "SMS"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "change_set_id": "cs_notif_7781",
    "status": "APPLIED",
    "notification_id": "notif_draft_12"
  },
  "meta": {},
  "warnings": []
}
```
