# API Specification: `premortem`

> Owner: `P2`  
> Base Path: `/api/v1/premortem`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The pre-mortem module provides time-travel simulation and historical risk playback. By executing each module's `public.risks(session, as_of_time)` across hourly discrete intervals over the 4-day festival timeline (Oct 29 08:00 to Nov 01 22:00), the pre-mortem predicts peak stress points before they materialize live.

---

## 2. Endpoints

### 2.1 `GET /api/v1/premortem/timeline`
- **Description**: Returns hourly risk severity and attention scores across all domains over the festival horizon.
- **Query Parameters**:
  - `start_time` (ISO-8601 string, optional)
  - `end_time` (ISO-8601 string, optional)
  - `min_severity` (int, default: 2)
- **Response `200 OK`**:
```json
{
  "data": {
    "intervals": [
      {
        "timestamp": "2026-10-30T18:00:00Z",
        "total_risks": 14,
        "max_severity": 4,
        "peak_people_affected": 1601,
        "top_bottlenecks": [
          "Bed demand peak (1,601 beds needed)",
          "Volunteer shift shortage (74 required vs 18 available)"
        ]
      }
    ]
  },
  "meta": {
    "simulated_hours": 96,
    "critical_threshold_hours": 3
  },
  "warnings": []
}
```
