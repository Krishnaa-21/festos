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
### 2026-10-30: P1/07-scheduling (Scheduler, Conflict Detector, Team Reconciliation, and Version Management)
- **Author**: P1 Lead
- **Branch**: `p1/07-scheduling`
- **Endpoints Added**:
  - `GET /api/v1/events`: List events with filtering.
  - `POST /api/v1/events`: Create event profile via ChangeService.
  - `GET /api/v1/events/{id}`: Event profile with requirements and rounds.
  - `PATCH /api/v1/events/{id}`: Update event profile via ChangeService.
  - `POST /api/v1/events/{id}/cancel`: Cancel event and cascade to active sessions.
  - `POST /api/v1/events/{id}/merge`: Merge event and repoint registrations.
  - `POST /api/v1/events/{id}/extend-duration`: Extend duration and cascade session end times.
  - `GET /api/v1/events/{id}/registrations`: Event registrations view.
  - `GET /api/v1/events/teams/provisional`: Provisional teams view reconciling 1,810 team registrations without team IDs.
  - `GET /api/v1/events/judges`: Judge registry and explicit UNASSIGNED slot gap analysis.
  - `POST /api/v1/events/judges`: Manual judge registration with competitor/contingent conflict detection.
  - `GET /api/v1/venues`: List venues with capacity and tags.
  - `POST /api/v1/venues`: Create venue via ChangeService.
  - `GET /api/v1/venues/{id}`: Venue profile with operating windows and feature tags.
  - `PATCH /api/v1/venues/{id}`: Update venue via ChangeService.
  - `GET /api/v1/venues/matrix/travel-times`: Travel time matrix with per-pair overrides.
  - `GET /api/v1/venues/matrix/compatibility`: ASSUMED venue-event compatibility mapping.
  - `POST /api/v1/schedule/generate`: Pure scheduler session generator with arrival waves (E, M, L), fairness proposals, and prototype benchmark comparison.
  - `GET /api/v1/schedule/versions`: Schedule versions with status, solver, and count metrics.
  - `POST /api/v1/schedule/versions/{id}/restore`: Restores full schedule version snapshot (requires FESTIVAL_DIRECTOR approval).
  - `GET /api/v1/schedule/sessions`: Event sessions list with volunteer & equipment requirements.
  - `POST /api/v1/schedule/sessions/{id}/move`: Move session with 60m downstream round cascade.
  - `POST /api/v1/schedule/sessions/{id}/change-venue`: Reassign venue with capacity violation check.
  - `GET /api/v1/schedule/conflicts`: Sweep-line conflict detector covering all 10 types.
  - `GET /api/v1/schedule/conflicts/{id}/resolutions`: Candidate time/venue moves ranked by conflicts resolved, new conflicts created, and people affected.
  - `POST /api/v1/schedule/conflicts/{id}/apply-resolution`: Apply selected ranked resolution.
  - `GET /api/v1/schedule/unscheduled`: Unscheduled participants report with reasons and alternatives.
  - `GET /api/v1/schedule/timeline`: Venue Gantt timeline data.
- **Public Functions Added**:
  - `services/events/public.py`: `summary`, `risks` (zero registration events), `dependents`
  - `services/venues/public.py`: `summary`, `risks` (unreachable venues), `dependents`
  - `services/schedule/public.py`: `summary`, `risks` (blocking conflicts in next 4h, unscheduled entrants, judge gaps), `dependents`, and report generators (`schedule_plan_csv`, `conflicts_report_csv`, `unscheduled_entrants_csv`, `resource_load_timeline_csv`)
- **Breaking Changes / Schema Migrations**:
  - Added `judges_needed` to `Event`.
  - Added `setup_time_min`, `teardown_time_min`, `feature_tags` to `Venue`.
  - Added `EventSession`, `ScheduleVersion`, `Conflict`, `Judge`, `ProvisionalTeam` models.
  - Baseline `ASSUMED` schedule generated during seeding with 312 provisional teams covering all 1,810 registrations without team IDs.
- **Action Required**:
  - Run `python -m app.seed load` or `make reset` to seed venue availability windows and baseline assumed schedule.

