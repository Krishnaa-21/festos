# API Specification: `impact`

> Owner: `P2`  
> Base Path: `/api/v1/impact`  
> Status: `ACTIVE`

---

## 1. Overview
The **Change Impact Engine & Blast Radius Analyzer** (`engines/impact`, spec sections 6.1 and 12.5) builds a global directed dependency graph across all FestOS modules.

### Dependency Chains Traversed
1. **Event & Venue Chain**:
   `Participant → Contingent → Registration → Event → Venue → Equipment → Vendor`
2. **Operations & Hospitality Chain**:
   `Participant → Arrival → Check-in → Accommodation → Meal requirements → Vendor`
3. **Logistics & Merchandise Chain**:
   `Participant → Merchandise eligibility → Stock → Distribution counter`

### Graph Traversal Engine
- Assembles nodes using every module's `public.dependents(entity_type, entity_id)` plus ORM relations.
- Performs breadth-first search (BFS) with:
  - **Depth Cap**: Default max depth of 5 steps to bound execution.
  - **Cycle Guard**: Visited-set tracking to prevent infinite loops on cyclical relationships.
  - **Per-Node Severity**: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
  - **People Affected**: Headcount propagation along dependent chains.
  - **Downstream Update Tracking**: Per-node status lifecycle (`PENDING` ➔ `UPDATED` ➔ `VERIFIED`).
- Registered as an automatic hook with `core.change_service` so any applied mutation can record its blast radius.

---

## 2. Endpoints

### 2.1 `POST /api/v1/impact/analyze`
- **Description**: Previews the blast radius and downstream consequences of any arbitrary operational change or proposed mutation without committing it.
- **Request Body**:
```json
{
  "entity_type": "hostel",
  "entity_id": "Hostel C",
  "action": "close",
  "reason": "Electrical fire alarm lockout",
  "parameters": {
    "block": "Hostel C"
  }
}
```
- **Response `200 OK`**:
```json
{
  "data": {
    "root": {
      "type": "hostel",
      "id": "Hostel C",
      "label": "Hostel Block C",
      "action": "close"
    },
    "tree": {
      "type": "hostel",
      "id": "Hostel C",
      "severity": "CRITICAL",
      "people_affected": 42,
      "children": [
        {
          "type": "room",
          "id": "rm_c101",
          "label": "Room C-101",
          "severity": "HIGH",
          "people_affected": 2,
          "update_status": "PENDING",
          "children": [
            {
              "type": "participant",
              "id": "P001",
              "label": "John Doe (CONT_DELHI)",
              "severity": "HIGH",
              "people_affected": 1,
              "update_status": "PENDING",
              "children": []
            }
          ]
        }
      ]
    },
    "counts_by_type": {
      "hostel": 1,
      "room": 21,
      "participant": 42,
      "meal_slot": 2
    },
    "severities": {
      "CRITICAL": 1,
      "HIGH": 21,
      "MEDIUM": 42,
      "LOW": 2
    },
    "total_people_affected": 42,
    "recommendations": [
      "Reallocate 42 displaced residents using minimal-change replanner",
      "Notify contingent leaders and hostel coordinator via SMS"
    ],
    "before_after_comparison": {
      "unplaced_before": 0,
      "unplaced_after": 42,
      "capacity_before": 710,
      "capacity_after": 668
    }
  },
  "meta": {
    "traversal_depth": 3,
    "nodes_visited": 66,
    "has_cycles": false
  },
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/impact/graph`
- **Description**: Inspects dependency connections for a specific entity across the unified festival graph.
- **Query Parameters**:
  - `entity` (string, required: format `<type>:<id>`, e.g. `participant:P001` or `vendor:VND03`)
  - `depth` (int, default: 3, max: 6)
- **Response `200 OK`**:
```json
{
  "data": {
    "entity": "participant:P001",
    "direct_dependents": [
      {"type": "contingent", "id": "CONT_DELHI"},
      {"type": "room", "id": "rm_c101"},
      {"type": "event", "id": "EVT_DANCE_SOLO"},
      {"type": "merchandise_claim", "id": "CLM_P001"}
    ],
    "graph": {
      "nodes": [
        {"id": "participant:P001", "type": "participant", "label": "John Doe"},
        {"id": "contingent:CONT_DELHI", "type": "contingent", "label": "IIT Delhi"},
        {"id": "room:rm_c101", "type": "room", "label": "Room C-101"}
      ],
      "edges": [
        {"from": "participant:P001", "to": "contingent:CONT_DELHI", "relation": "member_of"},
        {"from": "participant:P001", "to": "room:rm_c101", "relation": "occupies"}
      ]
    }
  },
  "meta": {},
  "warnings": []
}
```

---

### 2.3 `GET /api/v1/impact/preview`
- **Description**: Query-based shortcut for blast radius evaluation of entity actions.
- **Query Parameters**: `entity_type`, `entity_id`, `action`.
