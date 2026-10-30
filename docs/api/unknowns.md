# API Specification: `unknowns` (Field Verification)

> Owner: `P2` (P1 implementing field-verification parts for participants)  
> Base Path: `/api/v1/unknowns`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The `unknowns` module enforces FestOS Principle #4: **"UNKNOWN is a first-class value. A blank never means NO, consent, a gender, dietary clearance or absence of need."**
Key capabilities:
- **Field Verification Queue**: Real-time aggregation of unresolved `UNKNOWN` fields ranked deterministically by `Count x Criticality` (e.g., housing request criticality: 4, diet: 3, tshirt size: 2).
- **Verified Value Recording**: Mutations committed strictly through `ChangeService` (`unknowns.verify_field`), capturing verifier, source (e.g., `DESK_VERIFICATION`, `LEADER_SIGN_OFF`, `PHONE_CONFIRMATION`), and timestamp.
- **Data Owner Assignment**: Explicit ownership mapping for unverified fields to contingent leaders or specific desk teams.
- **Expiring Confirmation Tokens**: Signed, time-limited, field-scoped tokens enabling contingent leaders or desk volunteers to confirm participant fields directly: `POST /unknowns/confirm/{token}`.
- **Verification Audit Trail**: Full history of value transitions (`UNKNOWN` → `CLAIMED` → `VERIFIED`).

---

## 2. Endpoints

### 2.1 `GET /api/v1/unknowns/queue`
- **Description**: Returns the operational queue of unresolved unknown fields grouped and ranked by `count x criticality`.
- **Response `200 OK`**:
```json
{
  "data": {
    "total_unresolved_fields": 1284,
    "queue": [
      {
        "field": "accommodation_requested",
        "entity_type": "participant",
        "count": 418,
        "criticality": 4,
        "score": 1672,
        "owner": "ACCOMMODATION_LEAD",
        "impact_text": "Beds cannot be definitively blocked in Plan A/B without confirmed housing requirement.",
        "sample_entity_ids": ["P0012", "P0045", "P0102"]
      },
      {
        "field": "gender",
        "entity_type": "participant",
        "count": 417,
        "criticality": 4,
        "score": 1668,
        "owner": "ACCOMMODATION_LEAD",
        "impact_text": "Room allocation cannot enforce campus gender segregation safety constraints.",
        "sample_entity_ids": ["P0003", "P0019"]
      },
      {
        "field": "diet",
        "entity_type": "participant",
        "count": 394,
        "criticality": 3,
        "score": 1182,
        "owner": "FOOD_OPS_MANAGER",
        "impact_text": "Catering procurement buffers risk meal shortages or food waste.",
        "sample_entity_ids": ["P0001", "P0005"]
      },
      {
        "field": "tshirt_size",
        "entity_type": "participant",
        "count": 55,
        "criticality": 2,
        "score": 110,
        "owner": "MERCHANDISE_MANAGER",
        "impact_text": "Merchandise packing desk cannot pre-kit kit bags for arrival check-in.",
        "sample_entity_ids": ["P0211"]
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/unknowns/items`
- **Description**: Query individual participant records with unresolved unknown fields.
- **Query Parameters**:
  - `field` (string, required): e.g., `diet`, `gender`, `accommodation_requested`
  - `contingent_id` (string, optional): Filter by contingent
  - `page` (int, default: 1)
  - `page_size` (int, default: 50)
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "P0001",
        "name": "Rohan Deshmukh",
        "contingent_id": "C05",
        "field": "diet",
        "current_value": "UNKNOWN",
        "status": "UNKNOWN",
        "owner": "FOOD_OPS_MANAGER"
      }
    ],
    "total": 394,
    "page": 1,
    "page_size": 50,
    "total_pages": 8
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/unknowns/verify`
- **Description**: Record a verified field value through `ChangeService` (`unknowns.verify_field`). Updates the target entity and appends to `field_verification`.
- **Headers**:
  - `Idempotency-Key` (required UUID)
- **Request Body**:
```json
{
  "expected_version": 1,
  "reason": "Participant confirmed dietary preference in person at reception desk",
  "dry_run": false,
  "payload": {
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet",
    "value": "VEG",
    "source": "DESK_VERIFICATION",
    "verifier": "usr_desk_vol01"
  }
}
```
- **Response `200 OK`**: Standard Envelope containing `ChangeResult`.

---

### 2.4 `POST /api/v1/unknowns/token`
- **Description**: Issue a cryptographically signed, expiring token enabling a contingent leader or desk volunteer to submit verified values without full system access.
- **Request Body**:
```json
{
  "entity_type": "participant",
  "entity_id": "P0001",
  "field": "diet",
  "expires_in_minutes": 1440,
  "recipient_role": "LEADER"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "token": "eyJh...signed_token...",
    "expires_at": "2026-10-31T18:00:00Z",
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/unknowns/confirm/{token}`
- **Description**: Public verification endpoint using a signed confirmation token. Commits the verified value through `ChangeService`.
- **Request Body**:
```json
{
  "value": "VEG",
  "source": "LEADER_TOKEN_SUBMISSION",
  "comment": "Confirmed by contingent leader Rohan Deshmukh"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "status": "VERIFIED",
    "entity_id": "P0001",
    "field": "diet",
    "value": "VEG",
    "verified_at": "2026-10-30T14:22:00Z"
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `GET /api/v1/unknowns/history/{entity_type}/{entity_id}/{field}`
- **Description**: Retrieve chronological verification and status progression for a specific field on an entity.
- **Response `200 OK`**:
```json
{
  "data": {
    "entity_type": "participant",
    "entity_id": "P0001",
    "field": "diet",
    "verifications": [
      {
        "id": "ver_98765",
        "status": "VERIFIED",
        "value": "VEG",
        "source": "LEADER_TOKEN_SUBMISSION",
        "verified_by": "LEADER_TOKEN",
        "verified_at": "2026-10-30T14:22:00Z"
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
