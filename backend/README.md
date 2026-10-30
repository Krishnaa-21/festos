# FestOS Backend

Internal command centre backend for the Aarohan fest (EPINOIA 2026, IIM Indore).
Built with **FastAPI**, **SQLModel / SQLAlchemy 2**, **Pydantic v2**, and **SQLite (WAL)**.

---

## Architecture Overview

FestOS backend is structured as a **modular monolith** with strict ownership boundaries:

- **`app/core/`**: Shared platform infrastructure:
  - `config.py`: Application settings from `.env` via `pydantic-settings`.
  - `clock.py`: Timezone-aware clock with demo time simulation support.
  - `db.py`: SQLite engine with WAL mode and `use_scenario(scenario_id)` contextvar redirect.
  - `change_service.py`: Central mutation pipeline enforcing savepoint transactions, optimistic concurrency, and audit trails.
  - `registry.py`: Dynamic discovery of change handlers, seeders, participant sections, and public module contracts.
  - `idempotency.py`: Request hash and response replay engine.
  - `scoring.py`: Attention scores and urgency matrix calculators.
- **`app/schemas/common.py`**: Shared types (`Tri`, `Severity`, `Violation`, `Envelope`, `Page`, `RiskItem`, `ImpactReport`).
- **`app/models/`**: SQLModel database schemas partitioned by ownership (`participants`, `events`, `inventory`, `accommodation`, `vendors`, `ops`, `audit`, `change`).
- **`app/api/v1/`**: Auto-discovered route modules mounted dynamically at `/api/v1/<module>`.
- **`app/services/<module>/public.py`**: Inter-module integration contracts (`summary`, `risks`, `dependents`).

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Initialize Database & Seed
```bash
python -m app.seed reset
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Meta endpoint: [http://localhost:8000/api/v1/meta](http://localhost:8000/api/v1/meta)

---

## Testing & Linting

```bash
# Run tests
pytest -v backend/tests

# Run linter
ruff check backend
```
