# FestOS Integration Issues & Contract Requests

This register tracks missing or pending backend contracts between owners.

---

### Issue #06-01: Missing Backend Router for `imports` (Data Quality & Upload Wizard)
- **Status**: OPEN / IN DEVELOPMENT
- **Tagged Owner**: `@P2`
- **Requester**: P3 Frontend Lead
- **Module**: `imports`
- **Context**: Prompt 6 requires frontend upload wizard (files -> detected mapping -> validation summary -> quarantine review -> promote with reason), batch history, and data quality reporting.
- **Specification Reference**: Master Specification Section 16 & Data Conventions (Section 6), `raw_record`, `quarantine_row`, `import_batch`.
- **Requested Endpoints**:
  - `POST /api/v1/imports/upload` (Multipart CSV upload with preview & quarantine detection)
  - `GET /api/v1/imports/batches` (List of historical import batches)
  - `GET /api/v1/imports/quarantine` (List of quarantined rows with rejection reasons)
  - `POST /api/v1/imports/promote` (Promote validated rows to canonical tables with mandatory reason)
  - `GET /api/v1/imports/quality-report` (Quality issues summary and downloadable report)
- **Frontend Action**: Mocked via MSW handlers in `frontend/src/test/server.ts` and client fallback until backend router is merged.

---

### Issue #06-02: Missing Backend Router for `assumptions` (Assumptions Register & Inline Rationale Edit)
- **Status**: OPEN / IN DEVELOPMENT
- **Tagged Owner**: `@P2` (shared with `@P1`)
- **Requester**: P3 Frontend Lead
- **Module**: `assumptions`
- **Context**: Prompt 6 requires assumptions register table, inline editing with `ConfirmWithReason`, history drawer, and unverified assumption banner.
- **Specification Reference**: `Assumption` model in `app.models.change.py` and `app.seed.assumptions.py`.
- **Requested Endpoints**:
  - `GET /api/v1/assumptions` (List seeded assumptions with key, value, owner, source, reason, impact_if_changed, updated_at)
  - `PATCH /api/v1/assumptions/{key}` (Update assumption value with mandatory justification, audited via ChangeService)
  - `GET /api/v1/assumptions/{key}/history` (Audit timeline of assumption updates)
- **Frontend Action**: Mocked via MSW handlers in `frontend/src/test/server.ts` and client fallback until backend router is merged.
