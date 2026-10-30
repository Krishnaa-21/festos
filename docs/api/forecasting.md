# API Specification: `forecasting`

> Owner: `P2`  
> Base Path: `/api/v1/forecasting`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The forecasting module projects future operational demand across festival domains (arrival peaks, check-in queues, meal catering, accommodation beds, merchandise kits, equipment allocations, volunteer shifts) derived from current participant registrations and timetable schedules.

### Strict Data Provenance Rules:
- **`PROJECTION`**: Series mathematically derived from concrete database records (e.g., registered arrival flights/trains, confirmed dietary choices, scheduled timetable sessions).
- **`ASSUMPTION`**: Series driven by adjustable heuristic parameters or assumptions (e.g., check-in service rate per desk per minute, unconfirmed walk-in buffer).
- **Never present assumptions as predictions.** Every timeline bucket and graph series must carry its explicit provenance tag (`PROJECTION` or `ASSUMPTION`).

---

## 2. Endpoints

### 2.1 `GET /api/v1/forecasting/arrivals-queue`
- **Description**: Forecasts arrival volumes and simulates check-in queues using a discrete queue model ($M/D/c$ or fluid flow) based on declared arrival time distributions and editable desk service rate parameters.
- **Query Parameters**:
  - `desks_open` (int, default: 6): Number of active registration desks.
  - `service_rate_per_min` (float, optional): Average participants processed per desk per minute (defaults to system assumption `checkin_service_rate_per_min` = 0.5, i.e., 2 mins per participant).
  - `start_time` (ISO-8601 string, optional)
  - `end_time` (ISO-8601 string, optional)
- **Response `200 OK`**:
```json
{
  "data": {
    "parameters": {
      "desks_open": 6,
      "service_rate_per_desk_per_min": 0.5,
      "service_capacity_per_hour": 180,
      "parameter_source": "ASSUMPTION"
    },
    "timeline": [
      {
        "timestamp": "2026-10-29T10:00:00Z",
        "expected_arrivals": 210,
        "arrivals_series_type": "PROJECTION",
        "queue_length_start": 0,
        "processed_count": 180,
        "queue_length_end": 30,
        "wait_time_minutes": 10.0,
        "queue_series_type": "ASSUMPTION"
      },
      {
        "timestamp": "2026-10-29T11:00:00Z",
        "expected_arrivals": 250,
        "arrivals_series_type": "PROJECTION",
        "queue_length_start": 30,
        "processed_count": 180,
        "queue_length_end": 100,
        "wait_time_minutes": 33.3,
        "queue_series_type": "ASSUMPTION"
      }
    ],
    "peak_queue_hour": "2026-10-29T11:00:00Z",
    "max_queue_length": 100,
    "max_wait_time_minutes": 33.3
  },
  "meta": {
    "arrival_data_points": 1420,
    "unspecified_arrival_count": 181
  },
  "warnings": [
    "181 participants have UNKNOWN arrival times; assumed evenly distributed across daytime arrival windows."
  ]
}
```

---

### 2.2 `GET /api/v1/forecasting/demand-timeline`
- **Description**: Consolidated hourly multi-domain demand forecast for meals, accommodation beds, merchandise kits, equipment, and volunteers across the festival horizon.
- **Query Parameters**:
  - `domain` (string, optional): Filter by `MEALS`, `ACCOMMODATION`, `MERCHANDISE`, `EQUIPMENT`, `VOLUNTEERS`, or `ALL` (default).
- **Response `200 OK`**:
```json
{
  "data": {
    "timeline": [
      {
        "timestamp": "2026-10-30T13:00:00Z",
        "meals": {
          "total_demand": 1600,
          "confirmed_veg": 950,
          "confirmed_nonveg": 420,
          "confirmed_jain": 130,
          "unconfirmed_buffer": 100,
          "series_type": "PROJECTION",
          "buffer_series_type": "ASSUMPTION"
        },
        "accommodation": {
          "confirmed_beds_demanded": 1380,
          "possible_beds_demanded": 180,
          "total_beds_available": 1580,
          "deficit": 0,
          "series_type": "PROJECTION"
        },
        "equipment": {
          "active_scheduled_events": 6,
          "units_demanded": 48,
          "series_type": "PROJECTION"
        },
        "volunteers": {
          "volunteers_required": 54,
          "volunteers_scheduled": 42,
          "gap": 12,
          "series_type": "PROJECTION"
        }
      }
    ],
    "merchandise_summary": {
      "tshirt_size_breakdown": {
        "S": { "demand": 210, "stock": 250, "series_type": "PROJECTION" },
        "M": { "demand": 580, "stock": 600, "series_type": "PROJECTION" },
        "L": { "demand": 420, "stock": 400, "shortage": 20, "series_type": "PROJECTION" },
        "XL": { "demand": 190, "stock": 200, "series_type": "PROJECTION" },
        "UNKNOWN": { "demand": 55, "buffer_policy": "ALLOCATE_M_L", "series_type": "ASSUMPTION" }
      }
    }
  },
  "meta": {
    "data_points": 87
  },
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/forecasting/reports/{name}`
- **Description**: Generates exportable, structured analytical reports for festival forecasting outputs.
- **Path Parameters**:
  - `name` (string, required): One of `arrivals_queue`, `meal_demand`, `accommodation_capacity`, `volunteer_gap`, `merchandise_projection`.
- **Query Parameters**:
  - `format` (string, default: `json`, options: `json`, `csv`)
- **Response `200 OK`**:
```json
{
  "data": {
    "report_name": "arrivals_queue",
    "generated_at": "2026-10-31T04:15:00Z",
    "summary": "Peak arrival queue of 100 participants expected at 2026-10-29 11:00 UTC",
    "records_count": 87,
    "rows": [
      {
        "timestamp": "2026-10-29T10:00:00Z",
        "arrivals_projected": 210,
        "processed": 180,
        "queue_end": 30,
        "wait_minutes": 10.0
      }
    ]
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.4 `GET /api/v1/forecasting/crowd`
- **Description**: Backward-compatible venue-level crowd flow forecast.
- **Response `200 OK`**: Standard Envelope containing venue crowd projections.

---

### 2.5 `GET /api/v1/forecasting/bed-demand`
- **Description**: Dedicated accommodation bed demand timeline partitioned by confirmed vs possible demand.
- **Response `200 OK`**: Standard Envelope containing bed demand series.

---

### 2.6 `GET /api/v1/forecasting/resource-load`
- **Description**: Dedicated equipment and volunteer load over timetable event schedules.
- **Response `200 OK`**: Standard Envelope containing resource timeline series.
