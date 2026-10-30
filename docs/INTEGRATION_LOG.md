# FestOS Integration Log

Append an entry here after each merged prompt or feature branch.

Format:
- **Date**: YYYY-MM-DD
- **Prompt / Feature**: e.g. P1/01-foundation
- **Author / Owner**: P1 | P2 | P3
- **Endpoints Added**: list of paths
- **Public Functions Added**: module public contracts
- **Breaking Changes / Schema Migrations**: notes for teammates
- **Action Required**: commands to run after pulling

---

## Log Entries

### 2026-10-30: P1/01-foundation (Interface-First Foundation)
- **Author**: P1 Lead
- **Branch**: `p1/01-foundation`
- **Endpoints Added**:
  - `GET /health`
  - `GET /api/v1/meta`
  - `POST /api/v1/_example/items`
- **Public Functions Added**:
  - `services/<module>/public.py` for all 32 modules with `summary`, `risks`, and `dependents`
- **Breaking Changes / Schema Migrations**:
  - Initial foundation schema created (all canonical models, unique merch claim, stay assignment constraints, append-only audit).
  - No database migration required; use `make reset` or `python -m app.seed reset`.
- **Action Required**:
  - Run `make setup` or `pip install -r backend/requirements.txt`
  - Run `python -m app.seed load`

### 2026-10-30: P2/02-import (Raw Data Pack Ingestion & Quality Engine)
- **Author**: P2 Lead
- **Branch**: `p2/02-import`
- **Endpoints Added**:
  - `POST /api/v1/imports` (Multipart upload with tolerant CSV parser and dry-run)
  - `GET /api/v1/imports` (Paginated import batch history)
  - `GET /api/v1/imports/{id}` (Batch detail and status)
  - `GET /api/v1/imports/{id}/issues` (Quarantine rows with reason codes)
  - `POST /api/v1/imports/{id}/promote` (Atomic transfer to canonical tables via ChangeService)
  - `GET /api/v1/data-quality` (Full data quality report, reconciliation summary, JSON/CSV export)
  - `GET /api/v1/assumptions` (List assumptions with typed parsing and filter)
  - `GET /api/v1/assumptions/{key}` (Get single assumption)
  - `PUT /api/v1/assumptions/{key}` (Audited update via ChangeService)
  - `GET /api/v1/assumptions/{key}/history` (Assumption audit history)
  - `GET /api/v1/assumptions/{key}/dependents` (Preview dependent modules)
- **Public Functions Added**:
  - `services/imports/public.py`: `summary`, `risks` (unresolved quarantine, UNKNOWN gender/diet bottlenecks), `dependents`
  - `services/assumptions/public.py`: `summary`, `risks` (cleaning buffer tight, minor threshold lax, placeholder assumptions), `dependents`
  - `services/assumptions/service.py`: `get_assumption(key)` with in-memory caching and ChangeService-driven invalidation
- **Breaking Changes / Schema Migrations**:
  - Added operational models `ImportBatchMetadata` and `StagedRecord` in `app.models.ops`.
  - Raw rows are preserved byte-for-byte in `raw_record`; invalid intervals routed to `quarantine_row`.
  - Re-imports are idempotent based on SHA-256 batch content hash.
- **Action Required**:
  - Run `make reset` or `python -m app.seed reset` (runs seeder order 10, importing and promoting all 11 raw CSVs).

