# API Specification: `impact`

> Owner: `P2`  
> Base Path: `/api/v1/impact`  
> Status: `IMPLEMENTED`

---

## 1. Overview
The impact module computes downstream dependency cascades and blast radius metrics across the festival domain model. When an operational entity (hostel, event, venue, equipment, vendor) changes or fails, the impact engine traverses all registered `public.dependents()` functions to assemble the unified impact graph.

---

## 2. Endpoints

### 2.1 `GET /api/v1/impact/preview`
- **Description**: Evaluates the cascaded impact graph and blast radius for a proposed operational change without writing to the database.
- **Query Parameters**:
  - `entity_type` (string, e.g. `hostel`, `venue`, `event`, `vendor`, `equipment`)
  - `entity_id` (string, e.g. `Hostel C`, `VEN01`, `VND05`)
  - `action` (string, e.g. `close`, `cancel`, `delay`, `shutdown`)
- **Response `200 OK`**:
```json
{
  "data": {
    "root_change": {
      "entity_type": "hostel",
      "entity_id": "Hostel C",
      "action": "close"
    },
    "nodes": [
      {
        "type": "room",
        "id": "HC-101",
        "label": "Room HC-101",
        "severity": 3,
        "people_affected": 4,
        "depth": 1,
        "status": "DISRUPTED"
      },
      {
        "type": "participant",
        "id": "P0145",
        "label": "Aarav Sharma",
        "severity": 4,
        "people_affected": 1,
        "depth": 2,
        "status": "UNPLACED"
      }
    ],
    "counts_by_type": {
      "room": 40,
      "participant": 160,
      "shuttle_route": 2
    },
    "recommendations": [
      "Reallocate 160 participants to Hotel City Inn (Property EXT01)",
      "Dispatch 4 additional shuttle trips between 16:00 and 18:00"
    ]
  },
  "meta": {
    "total_nodes": 202,
    "max_depth": 3
  },
  "warnings": []
}
```
