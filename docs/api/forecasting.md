# API Specification: `forecasting`

> Owner: `P2`  
> Base Path: `/api/v1/forecasting`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The forecasting module calculates demand projections over time for accommodation beds, shuttle loads, venue capacities, food meal-slots, and volunteer coverage. Projections distinguish between `CONFIRMED` demand and `POSSIBLE` (unknown housing/attendance) demand.

---

## 2. Endpoints

### 2.1 `GET /api/v1/forecasting/bed-demand`
- **Description**: Returns bed demand timeline partitioned into on-campus capacity, external capacity, confirmed demand, and possible demand over 1-hour buckets.
- **Response `200 OK`**:
```json
{
  "data": {
    "timeline": [
      {
        "timestamp": "2026-10-30T18:00:00Z",
        "campus_capacity": 710,
        "external_capacity": 740,
        "confirmed_demand": 1420,
        "possible_demand": 181,
        "deficit": 151
      }
    ],
    "peak_timestamp": "2026-10-30T18:00:00Z",
    "peak_demand": 1601
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/forecasting/resource-load`
- **Description**: Returns equipment and volunteer load over simultaneous schedule sessions.
- **Response `200 OK`**:
```json
{
  "data": {
    "timeline": [
      {
        "timestamp": "2026-10-30T10:00:00Z",
        "volunteers_required": 74,
        "volunteers_on_shift": 18,
        "volunteer_gap": 56,
        "equipment_units_in_use": 42
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```
