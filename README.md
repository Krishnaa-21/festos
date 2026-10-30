# FestOS

FestOS is the internal command centre for the **Aarohan fest (EPINOIA 2026, IIM Indore)**.

It is a mission-critical operational cockpit designed to manage:
- ~2,400 expected vs 2,836 raw participants across 38 contingents
- 31 events, 9 venues, 14 food & beverage vendors, and 48 core staff
- 200 campus rooms (710 beds) + 6 external properties (740 beds)
- Real-time incident response, accommodation solvers, and unknown burn-downs.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLModel / SQLAlchemy 2, SQLite (WAL mode) / PostgreSQL.
- **Frontend**: React 18, Vite, TypeScript (strict), TailwindCSS, TanStack Query, React Router, openapi-typescript.
- **Ops**: Docker Compose, Makefile, GitHub Actions CI.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm

### Local Setup
```bash
# Clone and enter repo
git clone <repo-url>
cd festos

# Copy environment template
cp .env.example .env

# Set up dependencies
make setup

# Run database setup & seeding
make reset

# Start development servers
# Terminal 1: Backend
make dev-api

# Terminal 2: Frontend
make dev-web
```

API is available at [http://localhost:8000](http://localhost:8000) (Docs at [/docs](http://localhost:8000/docs)).  
Web UI is available at [http://localhost:5173](http://localhost:5173).

---

## Development Workflow & Parallel Ownership

Three engineers develop in parallel with zero merge collisions:
- **P1**: Core infrastructure, schemas, participants, contingents, events, venues, schedule, logistics, merchandise, staff, transport, dashboard, scenarios, reports.
- **P2**: Accommodation, vendors, food, check-in, finance, notifications, incidents, impact analysis, unknowns, pre-mortem, forecasting.
- **P3**: Authentication, audit, approvals, overrides, and frontend client application.

Refer to [`docs/FESTOS_CONTEXT.md`](docs/FESTOS_CONTEXT.md) and [`CODEOWNERS`](CODEOWNERS) for details.
