# API Specification: `reports`

> Owner: `P1`  
> Base Path: `/api/v1/reports`  
> Status: `DESIGNED`

---

## 1. Overview
The **Reports & Export Registry** provides authoritative, auditable generation and download of all 20 spec-mandated operational artifacts (Spec Section 14) and the post-festival comprehensive analysis (Spec Section 6.16).

### Key Guarantees:
1. **Spec 14 Complete Coverage**: 20 standard reports covering reconciliation, data quality, 3 accommodation plans (A/B/C), shortage, schedule, conflicts, inventory, equipment gaps, vendor coverage & compliance, staff coverage, timelines, assumptions markdown, incidents, and audit trails.
2. **CSV Injection Neutralization**: Any cell starting with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) is neutralised by prepending `'` to prevent DDE / spreadsheet execution vulnerabilities.
3. **Role-Based Masking & RBAC**: Exports strictly enforce actor role permissions. Sensitive participant fields (guardian, contact, medical, room numbers) are masked or redacted according to `core.masking`. Unauthorized report categories (e.g. Volunteer requesting audit or finance) return `403 FORBIDDEN`.
4. **Export Audit Trail**: Every individual report download and bundle zip generation produces an immutable audit event (`report.exported`) recording actor, timestamp, report name, row count, and role.
5. **Post-Festival Synthesis**: Aggregates live system state and the append-only audit trail into both HTML (styled executive dossier) and CSV formats, detailing participant attendance, bed utilization, event completions, inventory depreciation, vendor SLAs, incidents, expenses, and unpaid settlements.

---

## 2. Endpoints

### 2.1 `GET /api/v1/reports`
Returns the catalog of all 20 available reports with access permissions and metadata.

- **Query Parameters**: None
- **Response `200 OK`**:
```json
{
  "data": [
    {
      "name": "reconciliation_report.csv",
      "title": "Participant Reconciliation Report",
      "format": "csv",
      "category": "participants",
      "required_permission": "reconciliation:export",
      "description": "Explains participant counts, raw vs canonical records, and duplicate clusters"
    },
    {
      "name": "accommodation_plan_A.csv",
      "title": "Accommodation Plan A (Cohesion First)",
      "format": "csv",
      "category": "accommodation",
      "required_permission": "accommodation:export",
      "description": "Contingent cohesion prioritized bed assignments"
    },
    {
      "name": "accommodation_plan_B.csv",
      "title": "Accommodation Plan B (Cost First)",
      "format": "csv",
      "category": "accommodation",
      "required_permission": "accommodation:export",
      "description": "On-campus maximization minimizing external lodging expense"
    },
    {
      "name": "accommodation_plan_C.csv",
      "title": "Accommodation Plan C (Balanced)",
      "format": "csv",
      "category": "accommodation",
      "required_permission": "accommodation:export",
      "description": "Weighted compromise across cohesion, cost, and travel proximity"
    },
    {
      "name": "assumptions.md",
      "title": "Operational Assumptions Register",
      "format": "md",
      "category": "assumptions",
      "required_permission": "assumptions:export",
      "description": "All system parameters, buffers, weights, and ownership metadata"
    }
  ],
  "meta": {
    "total_reports": 20
  },
  "warnings": []
}
```

---

### 2.2 `GET /api/v1/reports/{name}`
Generates and downloads a specific report file.

- **Path Parameters**:
  - `name`: File name (e.g. `reconciliation_report.csv`, `schedule_plan.csv`, `assumptions.md`)
- **Query Parameters**:
  - `mask`: bool (optional, default: true; false requires `*:sensitive` role permission)
- **Response `200 OK`**:
  - `Content-Type`: `text/csv; charset=utf-8` or `text/markdown; charset=utf-8`
  - `Content-Disposition`: `attachment; filename="{name}"`
  - Content with neutralized CSV cells.

---

### 2.3 `GET /api/v1/reports/bundle.zip`
Generates a zip archive containing all reports the caller is authorized to view, alongside a `MANIFEST.json`.

- **Response `200 OK`**:
  - `Content-Type`: `application/zip`
  - `Content-Disposition`: `attachment; filename="festos_reports_bundle.zip"`

---

### 2.4 `GET /api/v1/reports/post-festival`
Produces the post-festival operational report synthesising live state and complete audit history.

- **Query Parameters**:
  - `format`: `html` (default) or `csv`
- **Response `200 OK`**:
  - When `format=html`: Returns complete styled HTML document ready for executive review.
  - When `format=csv`: Returns flat CSV summarizing KPIs across attendance, accommodation, events, inventory, vendors, incidents, and finance.

---

## 3. Error Responses
- `400 VALIDATION_ERROR`: Unknown report name.
- `403 FORBIDDEN`: Caller lacks required permission for the requested report.
- `500 INTERNAL_ERROR`: Failure generating report data.
