# API Specification: `commands`

> Owner: `P1`  
> Base Path: `/api/v1/commands`  
> Status: `DESIGNED`

---

## 1. Overview
The **Natural-Language Command Bar** provides an AI-assisted, operator-supervised entry point for festival commanders. It enables natural language queries, impact previews, and proposal generation while strictly enforcing the core safety principle:

> **AI proposes. Deterministic logic validates. Humans approve.**

### Architectural Guardrails:
1. **Strict Structured-Command Schema**: Only allowed intents can be produced (`show_impact`, `find_accommodation_for_unplaced`, `affected_events_by_equipment`, `alternative_vendors_for_diet`, `list_late_arrivals`, plus generic `query` and `navigate`). Intents cannot be invented on the fly; new capabilities require expanding the schema.
2. **Untrusted Model / Data-as-Data**: The LLM gets **zero tools and zero direct database access**. Retrieved data is injected as read-only values, never instructions. Sensitive context (medical, accessibility, contact details) is strictly omitted from LLM prompts.
3. **Deterministic Offline Fallback**: In the absence of an API key or during network partition / outage, a local RapidFuzz and regex keyword parser handles all standard spec queries deterministically.
4. **Mandatory Human-in-the-Loop for Mutations**: Read-only intents execute immediately. Any mutating intent creates a **PROPOSAL** via `ChangeService(dry_run=True)` with impact preview and recommendation cards, submitted to the `approvals` framework. Under no circumstance does natural text directly mutate database state.
5. **Auditing & Rate Limiting**: Every parse and execute attempt is logged to the immutable audit trail with actor details, raw prompt, structured output, and execution result. Endpoints are rate-limited.

---

## 2. Structured Command Schema

### 2.1 Intent Enum (`CommandIntent`)
| Intent | Type | Description | Required Permission |
|---|---|---|---|
| `show_impact` | Read-Only | Computes downstream impact graph for an entity (e.g. closing a hostel, cancelling a venue) | `impact:read` |
| `find_accommodation_for_unplaced` | Mutating | Runs allocation solver on unplaced participants and creates a proposal | `accommodation:write` |
| `affected_events_by_equipment` | Read-Only | Identifies events dependent on a specific equipment item or category | `logistics:read` |
| `alternative_vendors_for_diet` | Read-Only | Finds backup vendors capable of satisfying a dietary category | `food:read` |
| `list_late_arrivals` | Read-Only | Lists participants arriving after a given cutoff time | `participants:read` |
| `query` | Read-Only | General operational query across entities and counts | `dashboard:read` |
| `navigate` | Read-Only | Resolves UI destination route and deep link | `dashboard:read` |

---

## 3. Endpoints

### 3.1 `POST /api/v1/commands/parse`
Parses free text into a structured command schema and produces an operator explanation ("I interpreted this as...").

- **Rate Limit**: 60 requests / minute per client.
- **Request Body**:
```json
{
  "text": "Show the impact of closing Hostel C",
  "context": {
    "current_route": "/dashboard"
  }
}
```

- **Response `200 OK`**:
```json
{
  "data": {
    "command": {
      "intent": "show_impact",
      "parameters": {
        "entity_type": "room",
        "entity_id": "HOSTEL_C",
        "action": "close"
      },
      "is_mutating": false,
      "raw_text": "Show the impact of closing Hostel C"
    },
    "explanation": "I interpreted this as a request to analyze the operational impact of closing room/property 'Hostel C'.",
    "confidence": 0.95,
    "parser_mode": "LLM"
  },
  "meta": {
    "latency_ms": 42
  },
  "warnings": []
}
```

---

### 3.2 `POST /api/v1/commands/execute`
Executes a parsed structured command. Validates entity existence, parameter constraints, and caller RBAC permissions deterministically.
- Read-only commands execute and return results immediately.
- Mutating commands execute in `dry_run=True` mode, generating an approval proposal without writing database state.

- **Request Body**:
```json
{
  "command": {
    "intent": "find_accommodation_for_unplaced",
    "parameters": {
      "plan_kind": "C",
      "target_group": "all_unplaced"
    },
    "is_mutating": true,
    "raw_text": "Find accommodation for the unplaced participants"
  },
  "reason": "Emergency allocation request via command bar"
}
```

- **Response `202 Accepted` (Mutating Proposal Created)**:
```json
{
  "data": {
    "intent": "find_accommodation_for_unplaced",
    "status": "PROPOSAL_CREATED",
    "proposal_id": "prop_e817bc12",
    "approval_required": true,
    "change_set_id": null,
    "dry_run_result": {
      "affected_count": 48,
      "estimated_cost_inr": 28800.0,
      "solver_plan": "PLAN_C"
    },
    "impact": {
      "people_affected": 48,
      "nodes_count": 3
    },
    "message": "Mutating command validated. Created change proposal requiring Festival Director approval."
  },
  "meta": {
    "execution_time_ms": 115
  },
  "warnings": [
    "External beds required: 12 participants allocated to off-campus properties"
  ]
}
```

- **Response `200 OK` (Read-Only Execution)**:
```json
{
  "data": {
    "intent": "show_impact",
    "status": "EXECUTED",
    "proposal_id": null,
    "approval_required": false,
    "result": {
      "root_change": "room:HOSTEL_C (close)",
      "people_affected": 140,
      "nodes": [
        {"type": "room", "id": "HOSTEL_C", "label": "Hostel C", "severity": 3, "people_affected": 140},
        {"type": "participant", "id": "P0102", "label": "Affected Resident", "severity": 2, "people_affected": 1}
      ],
      "recommendations": [
        "Reallocate 140 occupants to external properties or Hostels A and B"
      ]
    }
  },
  "meta": {
    "execution_time_ms": 35
  },
  "warnings": []
}
```

---

## 4. Error Responses
- `400 VALIDATION_ERROR`: Missing parameters, unrecognized entities, or parameter constraint violation.
- `403 FORBIDDEN`: Caller lacks required permission for intent (e.g. `VOLUNTEER` executing `accommodation:write`).
- `429 RATE_LIMITED`: Exceeded 60 requests per minute limit.
