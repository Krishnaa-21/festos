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

### 2026-10-30: P1/04-participants (Canonical Participants, Contingents, Reconciliation, and Unknowns)
- **Author**: P1 Lead
- **Branch**: `p1/04-participants`
- **Endpoints Added**:
  - `GET /api/v1/participants`: List, fuzzy search, and multi-faceted filtering.
  - `POST /api/v1/participants`: Create participant via ChangeService.
  - `GET /api/v1/participants/{id}`: Single participant with role masking.
  - `PATCH /api/v1/participants/{id}`: Update profile via ChangeService.
  - `GET /api/v1/participants/{id}/360`: Full 360-degree operational view with dynamic sections.
  - `POST /api/v1/participants/{id}/status`: State machine transition publishing `participant.status_changed` on `core.bus`.
  - `GET /api/v1/participants/{id}/timeline`: Audit event timeline.
  - `GET /api/v1/contingents`: Contingents list with declared vs actual strength.
  - `GET /api/v1/contingents/{id}`: Contingent profile.
  - `GET /api/v1/contingents/{id}/status`: Contingent operational view (attendance, travel, events, diet, merchandise, alerts, housing fragmentation).
  - `PATCH /api/v1/contingents/{id}`: Update contingent profile via ChangeService.
  - `GET /api/v1/reconciliation/waterfall`: Counts panel and reconciliation waterfall explaining the 2,836 vs 2,842 vs 2,400 gap.
  - `GET /api/v1/reconciliation/duplicates`: Candidate pairs list filtered by classification or status.
  - `GET /api/v1/reconciliation/compare`: Side-by-side compare with linked registrations and claims.
  - `POST /api/v1/reconciliation/merge`: Merges duplicate into canonical record (blocks on conflicting merch claims).
  - `POST /api/v1/reconciliation/undo-merge/{merge_id}`: Byte-identical pre-merge state restoration.
  - `POST /api/v1/reconciliation/keep-separate`: Dismisses candidate pair with recorded rationale.
  - `GET /api/v1/reconciliation/history`: Chronological merge and revert history.
  - `GET /api/v1/reconciliation/flags`: Operational edge-case detection.
  - `GET /api/v1/unknowns/queue`: Unknown fields ranked by Count x Criticality.
  - `GET /api/v1/unknowns/items`: Unknown field items list.
  - `POST /api/v1/unknowns/verify`: Record verified values through ChangeService.
  - `POST /api/v1/unknowns/token`: Generate cryptographically signed, expiring confirmation token.
  - `POST /api/v1/unknowns/confirm/{token}`: Public / semi-public token confirmation endpoint.
  - `GET /api/v1/unknowns/history/{entity_type}/{entity_id}/{field}`: Field verification progression history.
- **Public Functions Added**:
  - `services/participants/public.py`: `summary`, `risks` (unresolved duplicates, incoming unknowns, overdue arrivals), `dependents`
  - `services/contingents/public.py`: `summary`, `risks` (strength mismatches), `dependents`
  - `services/reconciliation/public.py`: `summary`, `risks`, `dependents`
  - `services/unknowns/public.py`: `summary`, `risks`, `dependents`
- **Breaking Changes / Schema Migrations**:
  - Added `classification` to `DuplicateCandidate`.
  - Added `reason`, `reverted_at`, `reverted_by` to `MergeRecord`.
  - Added `data` field to `ChangeResult` in `core.change_service`.
  - Seed order 15 ingests `contingents.csv`, `participants.csv`, `events.csv`, `registrations.csv`, and runs pure deduplication engine persisting 312 candidates.
- **Action Required**:
  - Run `make reset` to drop/recreate tables and ingest the raw data pack.

