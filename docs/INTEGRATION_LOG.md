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

### 2026-10-30: P3/03-security-ui (Security, RBAC, Masking, Audit Hardening, Approvals, & Ops-Centre UI)
- **Author**: P3 Lead
- **Branch**: `p3/03-security-ui`
- **Endpoints Added**:
  - `POST /api/v1/auth/login` (JWT token issuance, argon2/bcrypt hashing, 5-attempt/15m lockout)
  - `POST /api/v1/auth/refresh`
  - `GET /api/v1/auth/me`
  - `GET /api/v1/auth/permissions` (Full RBAC matrix & caller permissions)
  - `POST /api/v1/auth/break-glass` (Emergency 15-min field elevation, mandatory reason, fully audited)
  - `GET /api/v1/auth/break-glass` (Active break-glass grants list)
  - `GET /api/v1/audit/events` (Paged, filtered, masked query API)
  - `GET /api/v1/audit/timeline/{entity_type}/{entity_id}` (Chronological entity history)
  - `GET /api/v1/audit/verify` (Cryptographic SHA-256 hash-chain verification)
  - `GET /api/v1/audit/export/csv` (CSV streaming respecting role field masking and export permissions)
  - `GET /api/v1/approvals` (Paged approval requests)
  - `GET /api/v1/approvals/policies` (Configured risk categories & approver role matrix)
  - `GET /api/v1/approvals/{id}`
  - `POST /api/v1/approvals/{id}/approve` (Executes pending ChangeSet on sign-off)
  - `POST /api/v1/approvals/{id}/reject` (Marks change rejected with mandatory reason)
  - `GET /api/v1/overrides` (Override register query API)
  - `POST /api/v1/overrides` (Records override with mandatory justification)
  - `GET /api/v1/overrides/{id}`
- **Public Functions Added / Hardened**:
  - `app/core/rbac.py`: Full RBAC matrix for all 9 roles, `has_permission`, `check_permission`, `get_role_permissions`, `get_all_permissions_matrix`
  - `app/core/masking.py`: `mask_fields(model, actor, entity_key, session)` supporting role exemptions and active break-glass checks; partial phone/email masking; `mask_log_message`; `export_allowed` decorator
  - `app/core/audit.py`: Append-only audit logging with SHA-256 hash chaining (`prev_hash`, `current_hash`), `verify_chain`
  - `app/core/overrides.py`: `record(...)` with mandatory reason validation
  - `app/core/approvals.py`: Configurable `APPROVAL_POLICIES`, `require(...)`, `approve_request(...)`, `reject_request(...)`
  - `app/services/{auth,audit,approvals,overrides}/public.py`: Implemented real read-only summary, risks, dependents contracts
  - `app/seed/users.py`: Seeder (order 20) provisioning 9 primary role accounts and extra volunteers with bcrypt hashes (documented in `docs/TEST_CREDENTIALS.md`)
- **Frontend Components & Shell**:
  - UI tokens & dark ops-centre theme (with light theme option) and HSL color palette
  - UI components in `src/components/ui`: `Button`, `Card`, `Badge` (severity icons + status + Tri-state YES/NO/UNKNOWN with distinct icons), `DataTable` (paged, sorted, virtualized/skeletons), `Modal`, `Drawer`, `ConfirmWithReason` (mandatory reason), `MaskedField` (click triggers emergency break-glass elevation), `WhyCard`, `Toast`, `Tabs`, `EmptyState`, `Skeleton`, `KpiTile`, `SeverityPill`, `ErrorBoundary`
  - `AppShell`: Permission-filtered sidebar per Section 18, operational clock, user profile menu, approvals bell with pending count badge, command bar with `/` shortcut, `g` then `o` overview navigation
  - `LoginPage`: Integrated login with quick role switcher for demonstration
  - `AuditPage`: Audit timeline, override register, approvals inbox with approve/reject, break-glass log with test bench, 9-role permission matrix, hash-chain verify modal, CSV export
  - Route guards: `RequireAuth` and `RequirePermission`
- **Breaking Changes / Schema Migrations**:
  - `audit_event` updated with `prev_hash`, `current_hash`, `approval_id`, `related_incident_id` and SQLite trigger preventing UPDATE / DELETE.
  - New database tables: `user` (with lockout tracking), `break_glass_grant`, `approval`, `override`.
- **Action Required**:
  - Backend: `python3 -m app.seed load`
  - Frontend: `npm install && npm run build`

