.PHONY: setup dev dev-api dev-web test lint gen-types seed reset demo samples clean

PYTHON ?= python
NPM ?= npm

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r backend/requirements.txt
	cd frontend && $(NPM) install

dev:
	@echo "Starting FestOS dev stack (API on 8000, Web on 5173)..."
	@echo "Run 'make dev-api' and 'make dev-web' in separate terminals, or use docker compose --profile dev up"

dev-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd frontend && $(NPM) run dev

test:
	$(PYTHON) -m pytest -v backend/tests
	cd frontend && $(NPM) run test

lint:
	ruff check backend
	cd frontend && $(NPM) run typecheck

gen-types:
	$(PYTHON) scripts/export_openapi.py --output frontend/openapi.json
	cd frontend && $(NPM) run gen-types

seed:
	cd backend && $(PYTHON) -m app.seed load

reset:
	cd backend && $(PYTHON) -m app.seed reset

demo:
	cd backend && $(PYTHON) -m app.seed reset
	@echo "Demo ready. Launching dev-api..."
	cd backend && uvicorn app.main:app --reload --port 8000

samples:
	cd backend && $(PYTHON) -m app.services.reports.samples

clean:
	rm -rf backend/festos.db *.db test.db scenarios/*.db
	rm -rf .pytest_cache .ruff_cache
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
