# API Specification: `auth`

> Owner: `P3`  
> Base Path: `/api/v1/auth`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Auth module provides authentication, session management, user identity inspection, granular RBAC permissions discovery, and emergency break-glass field elevation. It uses JWT bearer tokens with embedded role claims and securely hashes credentials using bcrypt/argon2. Accounts are automatically locked out for 15 minutes after 5 consecutive failed login attempts.

---

## 2. Endpoints

### 2.1 `POST /api/v1/auth/login`
- **Description**: Authenticate using email and password. Returns access and refresh JWT tokens.
- **Request Body**:
```json
{
  "email": "director@festos.internal",
  "password": "FestOSDirector2026!"
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "usr_dir_01",
      "email": "director@festos.internal",
      "full_name": "Festival Director",
      "role": "FESTIVAL_DIRECTOR"
    }
  },
  "meta": {},
  "warnings": []
}
```
- **Response `401 Unauthorized`**:
```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Invalid email or password",
    "details": null,
    "request_id": "req_auth_001"
  }
}
```
- **Response `429 Too Many Requests` (Lockout)**:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Account temporarily locked due to excessive failed attempts. Please wait 15 minutes.",
    "details": null,
    "request_id": "req_auth_002"
  }
}
```

---

### 2.2 `POST /api/v1/auth/refresh`
- **Description**: Issue a new access token using a valid refresh token.
- **Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/auth/me`
- **Description**: Get current authenticated user profile, assigned role, and effective permissions.
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "usr_dir_01",
    "email": "director@festos.internal",
    "full_name": "Festival Director",
    "role": "FESTIVAL_DIRECTOR",
    "contingent_id": null,
    "permissions": [
      "*:*"
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/auth/permissions`
- **Description**: Retrieve the comprehensive RBAC permission matrix for all festival roles. Used by frontend for dynamic UI capability mapping.
- **Response `200 OK`**:
```json
{
  "data": {
    "roles": {
      "FESTIVAL_DIRECTOR": ["*:*"],
      "ACCOMMODATION_LEAD": [
        "accommodation:read", "accommodation:write", "accommodation:approve", "accommodation:export", "accommodation:sensitive",
        "contingents:read", "participants:read", "venues:read", "reports:read"
      ],
      "EVENT_LEAD": [
        "events:read", "events:write", "events:approve", "events:export",
        "schedule:read", "schedule:write", "venues:read", "venues:write",
        "staff:read", "staff:write", "participants:read", "reports:read"
      ],
      "LOGISTICS_MANAGER": [
        "logistics:read", "logistics:write", "logistics:export",
        "venues:read", "events:read", "reports:read"
      ],
      "MERCHANDISE_MANAGER": [
        "merchandise:read", "merchandise:write", "merchandise:export",
        "participants:read", "contingents:read", "reports:read"
      ],
      "FOOD_OPS_MANAGER": [
        "food:read", "food:write", "food:export", "vendors:read", "vendors:write",
        "reports:read"
      ],
      "FINANCE_MANAGER": [
        "finance:read", "finance:write", "finance:approve", "finance:export",
        "vendors:read", "logistics:read", "reports:read", "reports:export"
      ],
      "VOLUNTEER": [
        "checkin:read", "checkin:write", "merchandise:read", "merchandise:write",
        "events:read", "venues:read"
      ],
      "AUDITOR": [
        "audit:read", "audit:export", "*:read"
      ]
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.5 `POST /api/v1/auth/break-glass`
- **Description**: Request temporary elevated emergency unmasking for a specific entity and field. Requires a mandatory rationale and expires automatically after the specified TTL (default 15 mins, max 60 mins).
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Request Body**:
```json
{
  "entity": "participant:P10023",
  "field": "medical_notes",
  "reason": "Emergency medical response team requested immediate allergy history",
  "minutes": 15
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "grant_id": "bgg_9a8b7c6d",
    "user_id": "usr_med_01",
    "entity": "participant:P10023",
    "field": "medical_notes",
    "reason": "Emergency medical response team requested immediate allergy history",
    "expires_at": "2026-10-30T13:45:00Z",
    "created_at": "2026-10-30T13:30:00Z"
  },
  "meta": {},
  "warnings": ["Break-glass access granted. This action has been logged in the immutable audit trail."]
}
```

---

### 2.6 `GET /api/v1/auth/break-glass`
- **Description**: List active break-glass grants for the current user or all active grants (for Director/Auditor).
- **Headers**:
  - `Authorization: Bearer <jwt>`
- **Response `200 OK`**:
```json
{
  "data": {
    "grants": [
      {
        "id": "bgg_9a8b7c6d",
        "user_id": "usr_med_01",
        "entity": "participant:P10023",
        "field": "medical_notes",
        "reason": "Emergency medical response team requested immediate allergy history",
        "expires_at": "2026-10-30T13:45:00Z",
        "is_active": true
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
