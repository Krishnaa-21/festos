# API Specification: Venues & Locations

> Owner: `P1`  
> Base Path: `/api/v1/venues`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The Venues module manages nine festival venues, capacity limits, operating windows, accessibility, equipment capabilities, editable feature tags, travel-time matrix, and the editable ASSUMED venue-event compatibility mapping.

---

## 2. Endpoints

### 2.1 `GET /api/v1/venues`
- **Description**: List all venues with capacity, availability windows, setup/teardown buffers, and feature tags.
- **Response `200 OK`**:
```json
{
  "data": {
    "items": [
      {
        "id": "V01",
        "name": "Main Stage",
        "capacity": 60,
        "indoor_outdoor": "indoor",
        "accessible": true,
        "setup_time_min": 15,
        "teardown_time_min": 15,
        "feature_tags": ["stage", "audio", "lights"],
        "availability_windows": "2026-10-30 08:00-22:00;2026-10-31 08:00-22:00;2026-11-01 08:00-20:00",
        "status": "AVAILABLE"
      }
    ],
    "total": 9
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/venues/{id}`
- **Description**: Detailed venue profile.
- **Response `200 OK`**:
```json
{
  "data": {
    "id": "V04",
    "name": "Amphitheatre",
    "capacity": 250,
    "indoor_outdoor": "outdoor",
    "accessible": true,
    "setup_time_min": 15,
    "teardown_time_min": 15,
    "feature_tags": ["open ground", "stage", "seating"],
    "availability_windows": "2026-10-30 08:00-22:00;2026-10-31 08:00-22:00;2026-11-01 08:00-20:00",
    "status": "AVAILABLE",
    "version": 1
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `POST /api/v1/venues`
- **Description**: Create a venue via `ChangeService` action `venue.create`.
- **Headers**: `Idempotency-Key` (UUID)

---

### 2.4 `PUT /api/v1/venues/{id}`
- **Description**: Update venue details via `ChangeService` action `venue.update`.
- **Headers**: `Idempotency-Key` (UUID)
- **Request Body**:
```json
{
  "capacity": 220,
  "setup_time_min": 20,
  "teardown_time_min": 20,
  "feature_tags": ["open ground", "stage"],
  "reason": "Adjusted seating after fire marshal inspection",
  "expected_version": 1
}
```

---

### 2.5 `GET /api/v1/venues/travel-times`
- **Description**: Return matrix of pairwise travel times between venues, falling back to default `venue_travel_min` (15 min).
- **Response `200 OK`**:
```json
{
  "data": {
    "default_travel_min": 15,
    "overrides": [
      {
        "from_venue_id": "V01",
        "to_venue_id": "V06",
        "travel_time_min": 25
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.6 `PUT /api/v1/venues/travel-times`
- **Description**: Upsert an explicit travel time override between two venues.
- **Request Body**:
```json
{
  "from_venue_id": "V01",
  "to_venue_id": "V08",
  "travel_time_min": 20
}
```

---

### 2.7 `GET /api/v1/venues/compatibility`
- **Description**: Get the editable ASSUMED venue-event compatibility mapping.
- **Response `200 OK`**:
```json
{
  "data": {
    "mapping": {
      "audio; seating": ["V04", "V02", "V03", "V01"],
      "projector; seating": ["V02", "V03", "V07", "V09"],
      "power; tables": ["V07", "V09", "V03", "V08"],
      "open ground": ["V04", "V05", "V06", "V08"],
      "quiet room": ["V09", "V07"],
      "stage; lights": ["V01"]
    },
    "status": "ASSUMED",
    "notes": "Derived from prototype requirements mapping; editable by Event Lead."
  },
  "meta": {},
  "warnings": ["Venue-event compatibility is ASSUMED because raw dataset contains no explicit venue assignments."]
}
```

---

### 2.8 `PUT /api/v1/venues/compatibility`
- **Description**: Update the venue-event compatibility mapping.
- **Request Body**:
```json
{
  "requirement_key": "stage; lights",
  "venue_ids": ["V01", "V04"],
  "reason": "Amphitheatre has lighting rigs"
}
```
