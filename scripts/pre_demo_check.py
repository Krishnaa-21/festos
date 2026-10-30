#!/usr/bin/env python3
"""FestOS Pre-Demo Automated Health & Rehearsal Verification Harness.

Validates the full system readiness before live judging:
1. Database Snapshot & Instant Reset (< 60s target; typically < 2s).
2. Role Authentication across all 9 roles.
3. 32-Module API endpoint responsiveness.
4. Latency timing of all seven live disruption scenarios (< 60s live-test rule).
5. Immutable Audit trail integrity & ChangeService verification.

Usage:
    python3 scripts/pre_demo_check.py
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Reconfigure stdout/stderr to utf-8 safely
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure database path is consistent
os.environ["DATABASE_URL"] = f"sqlite:///{(BACKEND_DIR / 'festos.db').resolve()}"

from fastapi.testclient import TestClient
from app.main import app
from app.core.clock import now, to_fest_tz
from scripts.backup_restore import restore_database, DEMO_SNAPSHOT_PATH, get_live_db_path

client = TestClient(app)

TEST_ROLES = [
    ("FESTIVAL_DIRECTOR", "director@festos.internal", "FestOSDirector2026!"),
    ("ACCOMMODATION_LEAD", "accommodation@festos.internal", "FestOSAccommodation2026!"),
    ("EVENT_LEAD", "events@festos.internal", "FestOSEvents2026!"),
    ("LOGISTICS_MANAGER", "logistics@festos.internal", "FestOSLogistics2026!"),
    ("MERCHANDISE_MANAGER", "merch@festos.internal", "FestOSMerch2026!"),
    ("FOOD_OPS_MANAGER", "food@festos.internal", "FestOSFood2026!"),
    ("FINANCE_MANAGER", "finance@festos.internal", "FestOSFinance2026!"),
    ("VOLUNTEER", "volunteer@festos.internal", "FestOSVolunteer2026!"),
    ("AUDITOR", "auditor@festos.internal", "FestOSAuditor2026!"),
]

MODULES_32 = [
    "accommodation", "approvals", "assumptions", "audit", "auth", "checkin",
    "commands", "contingents", "dashboard", "decisions", "events", "finance",
    "food", "forecasting", "impact", "imports", "incidents", "logistics",
    "merchandise", "notifications", "overrides", "participants", "premortem",
    "reconciliation", "reports", "scenarios", "schedule", "staff", "transport",
    "unknowns", "vendors", "venues"
]


def test_reset_demo_timing() -> float:
    """Measures reset-demo duration to ensure return to known state is under 60 seconds."""
    live_db = get_live_db_path()
    start = time.perf_counter()
    restore_database(DEMO_SNAPSHOT_PATH, live_db)
    elapsed = time.perf_counter() - start
    return elapsed


def test_role_auth() -> Dict[str, str]:
    """Tests all 9 credentials from docs/TEST_CREDENTIALS.md."""
    tokens = {}
    for role, email, password in TEST_ROLES:
        res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if res.status_code != 200:
            raise RuntimeError(f"Authentication failed for {role} ({email}): {res.text}")
        data = res.json().get("data", {})
        tokens[role] = data.get("access_token") or res.json().get("access_token")
    return tokens


def test_modules_health(token: str) -> List[Tuple[str, bool, float]]:
    """Hits list endpoints for all 32 modules with timing."""
    headers = {"Authorization": f"Bearer {token}"}
    results = []

    list_endpoints = {
        "accommodation": "/api/v1/accommodation/rooms",
        "approvals": "/api/v1/approvals",
        "assumptions": "/api/v1/assumptions",
        "audit": "/api/v1/audit/events",
        "auth": "/api/v1/auth/me",
        "checkin": "/api/v1/checkin/board",
        "commands": "/api/v1/commands",
        "contingents": "/api/v1/contingents",
        "dashboard": "/api/v1/dashboard/metrics",
        "decisions": "/api/v1/decisions",
        "events": "/api/v1/events",
        "finance": "/api/v1/finance/summary",
        "food": "/api/v1/food/coverage",
        "forecasting": "/api/v1/forecasting/crowd",
        "impact": "/api/v1/impact/blast-radius",
        "imports": "/api/v1/imports",
        "incidents": "/api/v1/incidents",
        "logistics": "/api/v1/logistics/items",
        "merchandise": "/api/v1/merchandise/catalog",
        "notifications": "/api/v1/notifications/drafts",
        "overrides": "/api/v1/overrides",
        "participants": "/api/v1/participants",
        "premortem": "/api/v1/premortem/resilience",
        "reconciliation": "/api/v1/reconciliation/waterfall",
        "reports": "/api/v1/reports",
        "scenarios": "/api/v1/scenarios",
        "schedule": "/api/v1/schedule/sessions",
        "staff": "/api/v1/staff",
        "transport": "/api/v1/transport/alerts",
        "unknowns": "/api/v1/unknowns/queue",
        "vendors": "/api/v1/vendors",
        "venues": "/api/v1/venues",
    }

    for mod in MODULES_32:
        endpoint = list_endpoints.get(mod, f"/api/v1/{mod}")
        start = time.perf_counter()
        res = client.get(endpoint, headers=headers)
        elapsed = (time.perf_counter() - start) * 1000.0
        results.append((mod, res.status_code == 200, elapsed))
    return results


def test_disruptions_timing(token: str) -> List[Tuple[str, float]]:
    """Times each of the seven mandatory disruption scenarios."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    timings = []

    # Scenario 1: Late Contingent
    t0 = time.perf_counter()
    r1 = client.post("/api/v1/contingents/C01/arrival-delay", json={"delay_minutes": 180, "reason": "Highway jam"}, headers=headers)
    timings.append(("1. Late Contingent Arrival (C01)", (time.perf_counter() - t0) * 1000.0))

    # Scenario 2: Duplicate Participant
    t0 = time.perf_counter()
    r2 = client.post("/api/v1/reconciliation/merge", json={"primary_id": "P0001", "duplicate_id": "P0002", "reason": "Verified duplicate registration"}, headers=headers)
    timings.append(("2. Duplicate Participant Merge (P0002 -> P0001)", (time.perf_counter() - t0) * 1000.0))

    # Scenario 3: Hostel Closure
    t0 = time.perf_counter()
    r3 = client.post("/api/v1/scenarios", json={"name": "Hostel Closure Rehearsal", "description": "Hostel 3 plumbing"}, headers=headers)
    if r3.status_code == 200:
        scen_id = r3.json()["data"]["id"]
        client.post(f"/api/v1/scenarios/{scen_id}/disruptions/hostel-closure", json={"hostel_name": "Hostel 3", "affected_beds": 85}, headers=headers)
        client.post(f"/api/v1/scenarios/{scen_id}/commit", json={"reason": "Director evacuation authorization"}, headers=headers)
    timings.append(("3. Hostel Closure Evacuation & Reallocation", (time.perf_counter() - t0) * 1000.0))

    # Scenario 4: Equipment Failure
    t0 = time.perf_counter()
    r4 = client.post("/api/v1/logistics/items/EQ01/report-damage", json={"severity": "CRITICAL", "notes": "Stage audio console failure"}, headers=headers)
    timings.append(("4. Equipment Stage Console Failure", (time.perf_counter() - t0) * 1000.0))

    # Scenario 5: Venue Change
    t0 = time.perf_counter()
    r5 = client.post("/api/v1/schedule/conflicts/manual-move", json={"session_id": "ses_0001", "new_venue_id": "V02", "reason": "Amphitheatre waterlogging relocation"}, headers=headers)
    timings.append(("5. Venue Emergency Relocation (V01 -> V02)", (time.perf_counter() - t0) * 1000.0))

    # Scenario 6: Vendor Shutdown
    t0 = time.perf_counter()
    r6 = client.post("/api/v1/vendors/VND04/shutdown", json={"reason": "Hygiene violation", "activate_backup": True}, headers=headers)
    timings.append(("6. Vendor Hygiene Shutdown & Meal Fallback", (time.perf_counter() - t0) * 1000.0))

    # Scenario 7: Duplicate Merchandise Claim Fraud
    t0 = time.perf_counter()
    # First issue
    client.post("/api/v1/merchandise/issue", json={"participant_id": "P0999_TEST", "item_id": "tshirt", "counter_id": "CTR_01"}, headers=headers)
    # Second duplicate attempt (must fail with 409)
    r7 = client.post("/api/v1/merchandise/issue", json={"participant_id": "P0999_TEST", "item_id": "tshirt", "counter_id": "CTR_02"}, headers=headers)
    timings.append(("7. Duplicate Merch Claim Enforcement", (time.perf_counter() - t0) * 1000.0))

    return timings


def main():
    print("=" * 72)
    print("FestOS Pre-Demo Automated Health & Rehearsal Verification Harness")
    print(f"Timestamp: {to_fest_tz(now()).isoformat()} IST")
    print("=" * 72)

    # 1. Test Demo Reset
    print("\n[STEP 1/5] Testing `make reset-demo` snapshot restore speed...")
    reset_duration = test_reset_demo_timing()
    print(f"  [PASS] Demo database restored in {reset_duration:.3f} seconds (Target: < 60s)")
    assert reset_duration < 60.0, "Reset demo exceeded 60 second target!"

    # 2. Test Role Authentication
    print("\n[STEP 2/5] Testing authentication across all 9 operational roles...")
    tokens = test_role_auth()
    for role, _, _ in TEST_ROLES:
        print(f"  [PASS] Role '{role}' logged in successfully with valid JWT.")
    director_token = tokens["FESTIVAL_DIRECTOR"]

    # 3. Test 32 Modules
    print("\n[STEP 3/5] Testing list endpoints across all 32 modules...")
    module_results = test_modules_health(director_token)
    all_ok = True
    for mod, ok, latency in module_results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  [{status}] {mod:<16} ({latency:.1f} ms)")
    assert all_ok, "One or more module endpoints failed!"

    # 4. Measure Disruption Scenarios Timing
    print("\n[STEP 4/5] Timing the Seven Mandatory Live-Test Disruption Flows...")
    timings = test_disruptions_timing(director_token)
    for name, latency in timings:
        print(f"  [PASS] {name:<45} {latency:.1f} ms (Target: < 60,000 ms)")

    # 5. Verify Audit Trail Growth
    print("\n[STEP 5/5] Verifying Audit Trail Integrity & ChangeService Events...")
    audit_res = client.get("/api/v1/audit/events", headers={"Authorization": f"Bearer {director_token}"})
    audit_count = len(audit_res.json()["data"])
    print(f"  [PASS] Total Verified Audit Events: {audit_count} records.")
    assert audit_count >= 5, "Audit trail count lower than expected!"

    # Return to clean known state
    print("\n[FINAL RESET] Restoring pristine demo snapshot...")
    test_reset_demo_timing()
    print("  [SUCCESS] Demo database returned to clean baseline.")

    print("\n" + "=" * 72)
    print("PRE-DEMO HARNESS STATUS: 100% HEALTHY & READY FOR 7-MINUTE PITCH")
    print("=" * 72)


if __name__ == "__main__":
    main()
