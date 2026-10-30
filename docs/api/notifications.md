# API Specification: `notifications`

> Owner: `P2`  
> Base Path: `/api/v1/notifications`  
> Status: `ACTIVE`

---

## 1. Overview
The **Notification Engine** (spec section 6.14) generates targeted operational message drafts from structured change events and incidents.

Key principles:
- **Five Specific Audiences**:
  1. `contingent_leaders`: Important housing, schedule, or dining updates affecting contingents.
  2. `volunteers`: Operational shift updates, venue changes, and participant directions.
  3. `vendors`: Service location shifts, capacity expansion, or shutdown alerts.
  4. `accommodation_coordinators`: Room closures, repair reallocations, and late arrivals.
  5. `event_organisers`: Schedule adjustments, venue transfers, and equipment updates.
- **Approval Gate**: In accordance with the core principle (*AI proposes, deterministic logic validates, humans approve*), message drafts **cannot be sent without explicit approval**.
- **Delivery Log & Mock Send**: Real-world external messaging is mocked for hackathon execution; every dispatch records to an auditable `NotificationDeliveryLog`.
- **Editable Templates**: Organizers can customize draft text, channels (`SMS`, `APP`, `EMAIL`, `WHATSAPP`), and recipient groups prior to dispatch.
- **Shared Generator**: Exposes `generate_drafts(change_set_or_incident)` for use across Prompt 11 (vendors/finance), Prompt 14 (incidents), and other modules.

---

## 2. Endpoints

### 2.1 `GET /api/v1/notifications/drafts`
- **Description**: Lists notification drafts with filtering by status, audience, and channel.
- **Query Params**: `status` (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `SENT`, `REJECTED`), `audience`, `channel`.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "not_vnd_01",
        "audience": "contingent_leaders",
        "channel": "SMS",
        "recipient": "All Contingent Leaders",
        "subject": "Dining Notice: Food Court A Reassignment",
        "body": "Dining Notice: Vendor A is offline. Lunch served at Vendor C counter (Food Court A).",
        "status": "PENDING_APPROVAL",
        "requires_approval": true,
        "related_change_set_id": "cs_vnd_shut_401",
        "related_incident_id": null,
        "created_at": "2026-10-31T12:05:00Z"
      }
    ],
    "total": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/notifications/drafts/{id}`
- **Description**: Returns detailed single draft information.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "not_vnd_01",
    "audience": "contingent_leaders",
    "channel": "SMS",
    "recipient": "All Contingent Leaders",
    "subject": "Dining Notice: Food Court A Reassignment",
    "body": "Dining Notice: Vendor A is offline. Lunch served at Vendor C counter (Food Court A).",
    "status": "PENDING_APPROVAL",
    "requires_approval": true,
    "template_key": "VENDOR_SHUTDOWN_LEADERS",
    "related_change_set_id": "cs_vnd_shut_401",
    "created_at": "2026-10-31T12:05:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/notifications/drafts/generate`
- **Description**: Generates a set of audience-targeted drafts from a structured change set or incident.
- **Request Body**:
```json
{
  "event_type": "VENDOR_SHUTDOWN",
  "change_set_id": "cs_vnd_shut_401",
  "incident_id": null,
  "context": {
    "vendor_name": "Vendor A",
    "replacement_name": "Vendor C",
    "affected_slots": ["LUNCH", "DINNER"],
    "location": "Food Court A",
    "reason": "Severe hygiene violation"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "drafts_generated": 5,
    "draft_ids": [
      "not_vnd_01",
      "not_vnd_02",
      "not_vnd_03",
      "not_vnd_04",
      "not_vnd_05"
    ],
    "audiences": [
      "contingent_leaders",
      "volunteers",
      "vendors",
      "accommodation_coordinators",
      "event_organisers"
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `PUT /api/v1/notifications/drafts/{id}`
- **Description**: Edits a draft's subject, body, or recipient before submission/approval.
- **Request Body**:
```json
{
  "subject": "URGENT Dining Notice: Food Court A Reassignment",
  "body": "Attention Leaders: Vendor A is closed by health inspector. Proceed to Vendor C immediately.",
  "channel": "SMS"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "not_vnd_01",
    "status": "PENDING_APPROVAL",
    "updated_at": "2026-10-31T12:10:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/notifications/drafts/{id}/approve`
- **Description**: Approves a notification draft for sending.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "not_vnd_01",
    "status": "APPROVED",
    "approved_by": "Festival Director",
    "approved_at": "2026-10-31T12:12:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `POST /api/v1/notifications/drafts/{id}/send`
- **Description**: Dispatches an approved notification draft (mock send). Strictly rejects sending if draft is unapproved.
- **Response `200 OK`**:
```json
{
  "data": {
    "delivery_id": "ndl_9012",
    "draft_id": "not_vnd_01",
    "status": "DELIVERED",
    "channel": "SMS",
    "recipient": "All Contingent Leaders",
    "dispatched_at": "2026-10-31T12:15:00Z"
  },
  "meta": {},
  "warnings": []
}
```
- **Error `422 Unprocessable Content`** (if unapproved):
```json
{
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "Notification draft 'not_vnd_01' cannot be sent without prior approval (current status: PENDING_APPROVAL).",
    "details": []
  }
}
```

---

### 2.7 `GET /api/v1/notifications/log`
- **Description**: Returns the complete delivery audit log of dispatched notifications.
- **Response `200 OK`**:
```json
{
  "data": {
    "logs": [
      {
        "id": "ndl_9012",
        "draft_id": "not_vnd_01",
        "recipient": "All Contingent Leaders",
        "channel": "SMS",
        "sent_at": "2026-10-31T12:15:00Z",
        "status": "DELIVERED",
        "provider": "MOCK_SMS_GATEWAY"
      }
    ],
    "total": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.8 `GET /api/v1/notifications/templates`
- **Description**: Returns all configurable notification templates across the 5 audiences.
- **Response `200 OK`**:
```json
{
  "data": {
    "templates": [
      {
        "key": "VENDOR_SHUTDOWN_LEADERS",
        "audience": "contingent_leaders",
        "channel": "SMS",
        "title": "Vendor Interruption Notice",
        "body_template": "Notice: Vendor {vendor_name} is offline. Meals are transferred to {replacement_name} at {location}."
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
