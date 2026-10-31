.PHONY: setup dev dev-api dev-web test verify-claims lint gen-types seed reset demo reset-demo smoke consistency backup restore snapshot samples clean

PYTHON ?= $(shell which python3 2>/dev/null || which python 2>/dev/null || echo python3)
NPM ?= npm

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r backend/requirements.txt
	cd frontend && $(NPM) install

dev:
	@echo "Starting FestOS dev stack (API on 8000, Web on 5173)..."
	@echo "Run 'make dev-api' and 'make dev-web' in separate terminals, or use docker compose up"

dev-api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd frontend && $(NPM) run dev

test:
	$(PYTHON) -m pytest -v backend/tests
	cd frontend && $(NPM) run test

verify-claims:
	$(PYTHON) scripts/verify_claims.py

pre-demo-check:
	$(PYTHON) scripts/pre_demo_check.py

smoke:
	$(PYTHON) scripts/smoke_all.py

consistency:
	$(PYTHON) scripts/check_cross_module_consistency.py

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

reset-demo:
	$(PYTHON) scripts/backup_restore.py restore data/snapshots/demo.db
	@echo "Known-good demo snapshot successfully restored."

demo:
	@if [ ! -f data/snapshots/demo.db ]; then \
		echo "Seeding initial database..."; \
		cd backend && $(PYTHON) -m app.seed reset; \
		$(PYTHON) scripts/backup_restore.py snapshot; \
	else \
		$(PYTHON) scripts/backup_restore.py restore data/snapshots/demo.db; \
	fi
	@echo "================================================================="
	@echo "FestOS Demo Stack Initialized with Seeded Data & Credentials."
	@echo "Launching backend API on port 8000..."
	@echo "================================================================="
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

backup:
	$(PYTHON) scripts/backup_restore.py backup

restore:
	$(PYTHON) scripts/backup_restore.py restore $(SOURCE)

snapshot:
	$(PYTHON) scripts/backup_restore.py snapshot

samples:
	cd backend && $(PYTHON) -m app.services.reports.samples

clean:
	rm -rf backend/festos.db *.db test.db scenarios/*.db
	rm -rf .pytest_cache .ruff_cache
	rm -rf frontend/dist
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
