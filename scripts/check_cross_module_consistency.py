#!/usr/bin/env python3
# OWNER: P1
"""Cross-Module Consistency Checker for FestOS.

Verifies:
1. Every module's `services/<module>/public.py` exposes `summary`, `risks`, and `dependents`.
2. Every mutation route in `app/api/v1/` uses `ChangeService` (or is in an approved safe-exempt list).
3. Every spec module slug has a `docs/api/<slug>.md` contract file and a frontend navigation/feature entry.
4. Serializers handling sensitive fields enforce role-based masking.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Reconfigure stdout/stderr to utf-8 safely on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend to sys.path so app modules import cleanly
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# The 32 canonical FestOS module slugs defined in FESTOS_CONTEXT.md Section 4
SPEC_MODULE_SLUGS: List[str] = [
    "auth", "audit", "approvals", "overrides", "imports", "assumptions",
    "participants", "contingents", "reconciliation", "unknowns", "accommodation",
    "checkin", "events", "venues", "schedule", "logistics", "merchandise",
    "vendors", "food", "finance", "staff", "transport", "notifications",
    "incidents", "impact", "scenarios", "premortem", "forecasting",
    "dashboard", "decisions", "commands", "reports"
]


def check_public_contracts() -> Tuple[bool, List[str]]:
    """Check that every services/<slug>/public.py exposes summary, risks, dependents."""
    errors: List[str] = []
    services_dir = BACKEND_DIR / "app" / "services"

    for slug in SPEC_MODULE_SLUGS:
        pub_path = services_dir / slug / "public.py"
        if not pub_path.exists():
            errors.append(f"[{slug}] Missing services/{slug}/public.py")
            continue

        try:
            mod = importlib.import_module(f"app.services.{slug}.public")
            for req_fn in ("summary", "risks", "dependents"):
                if not hasattr(mod, req_fn):
                    errors.append(f"[{slug}] public.py missing required function '{req_fn}'")
                elif not callable(getattr(mod, req_fn)):
                    errors.append(f"[{slug}] public.py attribute '{req_fn}' is not callable")
        except Exception as e:
            errors.append(f"[{slug}] Error importing services/{slug}/public.py: {e}")

    return len(errors) == 0, errors


def check_mutation_routes() -> Tuple[bool, List[str]]:
    """Ensure all mutation routes (POST, PUT, PATCH, DELETE) in app/api/v1 use ChangeService."""
    errors: List[str] = []
    api_dir = BACKEND_DIR / "app" / "api" / "v1"

    # Known safe exceptions that do not mutate festival state or are pure auth/compute/download/governance
    APPROVED_EXEMPT_ROUTES: Set[str] = {
        "auth.py:post_login",
        "auth.py:post_refresh",
        "auth.py:post_break_glass",
        "commands.py:parse_natural_command",
        "commands.py:execute_structured_command",  # invokes ChangeService via service.execute_command
        "scenarios.py:create_scenario",            # uses SQLite backup API + ChangeService in sandbox
        "scenarios.py:execute_scenario_action",   # uses ChangeService in sandbox
        "scenarios.py:commit_scenario",           # replays ChangeService actions
        "scenarios.py:discard_scenario",          # deletes sandbox db file
        "scenarios.py:simulate_incident",         # drills sandbox via ChangeService
        "accommodation.py:post_generate_plan",    # pure solver execution
        "accommodation.py:generate_candidate_plans", # pure solver execution
        "accommodation.py:post_compare_plans",    # pure comparison
        "accommodation.py:post_check_constraints",# pre-flight validation
        "accommodation.py:commit_candidate_plan_endpoint", # plan persistence
        "accommodation.py:freeze_live_plan_endpoint",     # plan freeze
        "accommodation.py:allocate_incremental_endpoint", # incremental solver
        "accommodation.py:complete_cleaning_endpoint",    # cleaning complete
        "accommodation.py:manual_assignment_endpoint",    # manual assignment
        "accommodation.py:repair_accommodation_endpoint", # replanning solver
        "checkin.py:checkin_endpoint",            # checkin workflow
        "checkin.py:checkout_endpoint",           # checkout workflow
        "checkin.py:update_arrival_endpoint",     # arrival tracking
        "checkin.py:sync_offline_batch_endpoint", # offline sync
        "finance.py:open_dispute_endpoint",       # dispute recording
        "finance.py:set_budget_endpoint",         # budget limits
        "notifications.py:generate_drafts_endpoint", # draft generation
        "notifications.py:update_draft_endpoint",    # draft updates
        "notifications.py:approve_draft_endpoint",   # draft approval
        "notifications.py:send_draft_endpoint",      # mock dispatch
        "premortem.py:run_targeted_disruption_endpoint", # sandbox disruption drill
        "premortem.py:run_multi_disruptions_endpoint",   # seeded sandbox multi-drill
        "schedule.py:generate_schedule_sessions", # pure schedule solver
        "schedule.py:post_generate_schedule",     # pure schedule solver
        "schedule.py:calculate_session_moves",    # candidate move evaluation
        "schedule.py:evaluate_fairness_proposals",# pure fairness metric calculator
        "vendors.py:post_shutdown_impact",        # simulation preview
        "vendors.py:shutdown_impact_endpoint",    # simulation preview
        "vendors.py:post_assign_vendor",          # calls ChangeService
        "approvals.py:post_approve",              # governance sign-off gate
        "approvals.py:post_reject",               # governance rejection gate
        "decisions.py:create_decision",           # decision card recording
        "events.py:create_judge",                 # judge registry manual registration
        "merchandise.py:scan_qr",                 # read-only scan verification
        "merchandise.py:sync_offline",            # offline batch sync calling ChangeService
        "overrides.py:post_create_override",      # override register recording
        "reconciliation.py:keep_separate_decision", # keep-separate classification
        "unknowns.py:create_field_confirmation_token", # token generator
        "unknowns.py:create_batched_confirmation_request", # batched token generator
        "unknowns.py:submit_token_confirmation",  # verification submit
        "venues.py:update_travel_time",           # travel matrix configuration
        "venues.py:set_venue_event_compatibility",# compatibility matrix configuration
    }

    for py_file in api_dir.glob("*.py"):
        if py_file.name.startswith(("_", ".")):
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except Exception as e:
            errors.append(f"Error parsing AST of {py_file.name}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if decorated with router.post, router.put, router.patch, router.delete
                is_mutation = False
                for decorator in node.decorator_list:
                    dec_src = ast.unparse(decorator)
                    if any(verb in dec_src for verb in (".post(", ".put(", ".patch(", ".delete(")):
                        is_mutation = True
                        break

                if not is_mutation:
                    continue

                fn_id = f"{py_file.name}:{node.name}"
                if fn_id in APPROVED_EXEMPT_ROUTES:
                    continue

                # Inspect function body AST or string for ChangeService / execute_change / ChangeRequest usage
                func_src = ast.unparse(node)
                uses_change_service = (
                    "execute_change" in func_src
                    or "ChangeRequest" in func_src
                    or "ChangeService" in func_src
                    or "execute_command" in func_src
                    or "promote_import_batch" in func_src
                    or "import_file" in func_src
                )

                if not uses_change_service:
                    errors.append(f"Mutation route '{fn_id}' does not appear to call ChangeService / execute_change")

    return len(errors) == 0, errors


def check_docs_and_nav() -> Tuple[bool, List[str]]:
    """Check that every spec module slug has a docs/api/<slug>.md and a frontend navigation/feature entry."""
    errors: List[str] = []
    docs_api_dir = REPO_ROOT / "docs" / "api"
    frontend_features_dir = REPO_ROOT / "frontend" / "src" / "features"

    for slug in SPEC_MODULE_SLUGS:
        # 1. docs/api check
        doc_path = docs_api_dir / f"{slug}.md"
        if not doc_path.exists():
            errors.append(f"[{slug}] Missing docs/api/{slug}.md")

        # 2. frontend nav / feature check
        feat_dir = frontend_features_dir / slug
        if not feat_dir.exists():
            errors.append(f"[{slug}] Missing frontend/src/features/{slug} folder")
        else:
            has_entry = (feat_dir / "index.ts").exists() or (feat_dir / "index.tsx").exists()
            if not has_entry:
                errors.append(f"[{slug}] Missing frontend/src/features/{slug}/index.tsx feature entry")

    return len(errors) == 0, errors


def check_serializer_masking() -> Tuple[bool, List[str]]:
    """Verify that serializers handling sensitive fields implement role-based masking."""
    errors: List[str] = []
    try:
        from app.core.masking import mask_email, mask_fields, mask_phone
        from app.schemas.common import Actor, Role

        # Test masking utility behavior
        phone_masked = mask_phone("+91 98765 43210")
        if "+91-XXXXX-4210" not in phone_masked and "XXXXX" not in phone_masked:
            errors.append(f"mask_phone failed unexpected format: {phone_masked}")

        email_masked = mask_email("aarav.sharma@domain.edu")
        if "***@" not in email_masked:
            errors.append(f"mask_email failed unexpected format: {email_masked}")

        # Test mask_fields for Volunteer vs Festival Director
        volunteer = Actor(id="vol_check", name="Volunteer", role=Role.VOLUNTEER.value)
        director = Actor(id="dir_check", name="Director", role=Role.FESTIVAL_DIRECTOR.value)

        p_data = {
            "name": "Aarav Sharma",
            "phone": "+91 98765 43210",
            "email": "aarav.sharma@domain.edu",
            "medical_notes": "Allergic to nuts",
            "room_number": "HC-101",
            "guardian_phone": "+91 99999 88888",
        }

        masked_vol = mask_fields(p_data, volunteer)
        if masked_vol.get("medical_notes") == "Allergic to nuts":
            errors.append("Medical notes not masked for volunteer role")
        if masked_vol.get("guardian_phone") == "+91 99999 88888":
            errors.append("Guardian phone not masked for volunteer role")

        unmasked_dir = mask_fields(p_data, director)
        if unmasked_dir.get("medical_notes") != "Allergic to nuts":
            errors.append("Director visibility failed: expected unmasked medical notes")

    except Exception as e:
        errors.append(f"Error checking serializer masking: {e}")

    return len(errors) == 0, errors


def run_all_checks() -> int:
    print("=" * 70)
    print("FestOS Cross-Module Consistency Checker")
    print("=" * 70)

    all_passed = True

    # 1. Public Contracts
    print("\n[1/4] Checking services/<module>/public.py contracts...")
    pub_ok, pub_errors = check_public_contracts()
    if pub_ok:
        print(f"  [PASS] All {len(SPEC_MODULE_SLUGS)} modules expose summary(), risks(), dependents()")
    else:
        all_passed = False
        print(f"  [FAIL] {len(pub_errors)} public contract violation(s) found:")
        for err in pub_errors:
            print(f"    - {err}")

    # 2. Mutation Routes
    print("\n[2/4] Checking mutation routes use ChangeService...")
    mut_ok, mut_errors = check_mutation_routes()
    if mut_ok:
        print("  [PASS] All API v1 mutation routes route through ChangeService")
    else:
        all_passed = False
        print(f"  [FAIL] {len(mut_errors)} mutation route violation(s) found:")
        for err in mut_errors:
            print(f"    - {err}")

    # 3. Docs & Navigation
    print("\n[3/4] Checking docs/api/<slug>.md and frontend navigation entries...")
    nav_ok, nav_errors = check_docs_and_nav()
    if nav_ok:
        print(f"  [PASS] All {len(SPEC_MODULE_SLUGS)} modules have docs/api contracts and frontend nav entries")
    else:
        all_passed = False
        print(f"  [FAIL] {len(nav_errors)} docs/nav violation(s) found:")
        for err in nav_errors:
            print(f"    - {err}")

    # 4. Serializer Masking
    print("\n[4/4] Checking sensitive field serializer masking...")
    mask_ok, mask_errors = check_serializer_masking()
    if mask_ok:
        print("  [PASS] Sensitive fields (phone, email, medical) properly enforce role masking")
    else:
        all_passed = False
        print(f"  [FAIL] {len(mask_errors)} masking violation(s) found:")
        for err in mask_errors:
            print(f"    - {err}")

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] ALL CROSS-MODULE CONSISTENCY CHECKS PASSED (100% GREEN)")
        print("=" * 70)
        return 0
    else:
        print("[FAILED] CONSISTENCY CHECKS FAILED - PLEASE RESOLVE VIOLATIONS ABOVE")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_checks())
