# OWNER: P2
"""Hardening validation tests for FestOS (Task 7: Validate the validators).

Tests deliberate data pack corruption and asserts clear, deterministic error reporting:
1. Missing mandatory columns -> MissingColumnsError with exact column list.
2. Malformed CSVs -> MalformedCSVError (null bytes, empty header, binary corruption).
3. Invalid dates and intervals -> quarantine rows with documented reason codes (INVALID_ARRIVAL_DEPARTURE_INTERVAL).
4. UNKNOWN values preserved -> corrupted strings map to UNKNOWN, never silently coerced.
5. Duplicate IDs & deduplication signals -> raw rows preserved, dedupe engine classifies signals properly.
6. Cross-pack integrity validation -> missing references, team ID omissions, and hygiene expiry detected.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.security import create_access_token
from app.engines.dedupe import compute_pair_similarity, soundex
from app.engines.importer.mapping import get_mapping_config
from app.engines.importer.normalizers import (
    normalize_accessibility,
    normalize_condition,
    normalize_datetime,
    normalize_diet,
    normalize_gender,
    normalize_housing_preference,
    normalize_tri,
)
from app.engines.importer.parser import (
    MalformedCSVError,
    MissingColumnsError,
    parse_csv_content,
)
from app.engines.importer.validator import (
    validate_cross_pack,
    validate_participant_row,
)
from app.main import app
from app.models.participants import Participant, QuarantineRow, RawRecord


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(
        data={"sub": "director_user", "role": "FESTIVAL_DIRECTOR", "permissions": ["*"]}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# =========================================================================
# 1. Missing Columns Validation
# =========================================================================

def test_missing_required_columns_raises_clear_error() -> None:
    """Deliberately omit required columns in participants CSV and verify clear MissingColumnsError."""
    # participants config requires 'id' and 'name'
    corrupted_csv = b"id,college,gender\nP001,Tech Inst,Male\n"
    
    with pytest.raises(MissingColumnsError) as exc_info:
        parse_csv_content(corrupted_csv, sheet_name="participants")
    
    err = exc_info.value
    assert "name" in err.missing_columns
    assert err.sheet_name == "participants"
    assert "Missing required columns in participants" in str(err)


def test_missing_columns_api_returns_422(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Verify HTTP API returns 422 with missing columns detail on bad upload."""
    # missing both required 'name' and 'contingent_id'
    corrupted_csv = b"id,college,phone\nP001,Tech Inst,9999999999\n"
    files = {"file": ("participants.csv", corrupted_csv, "text/csv")}
    
    res = client.post(
        "/api/v1/imports?sheet_name=participants",
        files=files,
        headers=auth_headers,
    )
    assert res.status_code == 422
    data = res.json()
    err_msg = data.get("error", {}).get("message", "") or data.get("detail", "")
    assert "Missing required columns" in err_msg
    assert "name" in err_msg
    assert "contingent_id" in err_msg


# =========================================================================
# 2. Malformed CSV Detection
# =========================================================================

def test_malformed_csv_null_byte_corruption() -> None:
    """Detect binary or null byte injection in CSV."""
    corrupted_csv = b"id,name,contingent_id\nP001,\x00Corrupted,C01\n"
    
    with pytest.raises(MalformedCSVError) as exc_info:
        parse_csv_content(corrupted_csv, sheet_name="participants")
    
    assert "null byte corruption" in str(exc_info.value).lower()


def test_malformed_csv_empty_header() -> None:
    """Detect CSV with empty or whitespace-only headers."""
    empty_csv = b"   ,   \n"
    
    with pytest.raises(MalformedCSVError) as exc_info:
        parse_csv_content(empty_csv, sheet_name="participants")
    
    assert "header row is missing or empty" in str(exc_info.value).lower()


def test_malformed_csv_empty_file() -> None:
    """Empty byte payload triggers MalformedCSVError."""
    with pytest.raises(MalformedCSVError):
        parse_csv_content(b"", sheet_name="participants")


# =========================================================================
# 3. Invalid Dates and Interval Quarantine
# =========================================================================

def test_arrival_after_departure_triggers_quarantine() -> None:
    """Participant with arrival_at >= departure_at must be quarantined, not staged."""
    csv_data = (
        b"id,name,contingent_id,arrival_at,departure_at\n"
        b"P_TIME_FAIL,Backwards Walker,C01,2026-11-02 18:00,2026-10-30 09:00\n"
        b"P_TIME_OK,Normal Walker,C01,2026-10-30 09:00,2026-11-02 18:00\n"
    )
    
    result = parse_csv_content(csv_data, sheet_name="participants")
    
    assert result.total_rows == 2
    assert result.imported_rows == 1
    assert result.quarantined_rows == 1
    
    # Check quarantine row record
    q_rec = result.quarantine_records[0]
    assert q_rec["reason_code"] == "INVALID_ARRIVAL_DEPARTURE_INTERVAL"
    assert q_rec["source_row_id"] == "P_TIME_FAIL"
    assert "P_TIME_FAIL" in q_rec["reason"]
    
    # Check raw record was still preserved
    assert len(result.raw_records) == 2
    assert any(r["source_row_id"] == "P_TIME_FAIL" for r in result.raw_records)


def test_unparseable_date_strings_normalize_to_none_gracefully() -> None:
    """Unparseable dates must return None instead of raising unhandled exceptions."""
    bad_dates = [
        "not-a-date",
        "2026-99-99",
        "32/13/2026 25:99:99",
        "undefined",
        "null",
        "",
    ]
    for bad in bad_dates:
        assert normalize_datetime(bad) is None


# =========================================================================
# 4. UNKNOWN Preservation Under Corrupted/Malformed Attributes
# =========================================================================

def test_corrupted_attributes_preserve_unknown() -> None:
    """Corrupted, alien, or empty values must resolve to UNKNOWN, never coerced to standard defaults."""
    # Gender
    assert normalize_gender("Alien") == "UNKNOWN"
    assert normalize_gender("???") == "UNKNOWN"
    assert normalize_gender("") == "UNKNOWN"
    assert normalize_gender(None) == "UNKNOWN"
    
    # Diet
    assert normalize_diet("Plastic") == "UNKNOWN"
    assert normalize_diet("???") == "UNKNOWN"
    assert normalize_diet(None) == "UNKNOWN"
    
    # Tri-state
    assert normalize_tri("maybe") == "UNKNOWN"
    assert normalize_tri("???") == "UNKNOWN"
    assert normalize_tri("") == "UNKNOWN"
    
    # Housing preference
    assert normalize_housing_preference("") == "UNKNOWN"
    assert normalize_housing_preference("null") == "UNKNOWN"
    
    # Accessibility
    acc = normalize_accessibility("unknown")
    assert acc["status"] == "UNKNOWN"
    assert acc["needs"] == []


# =========================================================================
# 5. Duplicate Detection & Signal Hardening
# =========================================================================

def test_dedupe_name_similarity_alone_never_reaches_likely() -> None:
    """Spec Section 8: Name similarity alone must NEVER reach LIKELY (requires supporting signals)."""
    p1 = {
        "id": "P_001",
        "name": "Ananya Sharma",
        "college": "College A",
        "contingent_id": "C_A",
        "phone": "9876543210",
        "age": 20,
    }
    # Exactly identical name, but completely different college, phone, age
    p2 = {
        "id": "P_002",
        "name": "Ananya Sharma",
        "college": "College B",
        "contingent_id": "C_B",
        "phone": "9123456780",
        "age": 22,
    }
    
    res = compute_pair_similarity(p1, p2)
    # Name alone cannot reach LIKELY (>= 0.85)
    assert res["classification"] != "LIKELY"
    assert res["classification"] != "EXACT"
    assert res["can_auto_merge"] is False


def test_dedupe_multi_signal_exact_match() -> None:
    """Identical name, phone, contingent, and age gives EXACT match."""
    p1 = {
        "id": "P_001",
        "name": "Ananya Sharma",
        "college": "College A",
        "contingent_id": "C_A",
        "phone": "9876543210",
        "age": 20,
    }
    p2 = {
        "id": "P_002",
        "name": "Ananya Sharma",
        "college": "College A",
        "contingent_id": "C_A",
        "phone": "9876543210",
        "age": 20,
    }
    
    res = compute_pair_similarity(p1, p2)
    assert res["score"] >= 0.85
    assert res["classification"] in ("LIKELY", "EXACT")


# =========================================================================
# 6. Cross-Pack Reference & Data Pack Validation
# =========================================================================

def test_cross_pack_validation_catches_corrupted_pack() -> None:
    """Validate cross_pack engine catches missing participants, missing events, team ID issues,
    contingent discrepancies, and expired hygiene certs."""
    participants = [{"id": "P_VALID_01", "name": "Valid User", "contingent_id": "C_01"}]
    events = [{"id": "EV_SOLO_01", "solo_team": "solo"}, {"id": "EV_TEAM_01", "solo_team": "team"}]
    contingents = [{"id": "C_01", "strength_declared": 20, "leader": "Missing Leader"}]
    vendors = [{"id": "V_01", "name": "Bad Food Co", "hygiene_certificate_expiry": "2026-10-15"}]
    
    registrations = [
        # Registration pointing to non-existent participant
        {"participant_id": "P_NON_EXISTENT", "event_id": "EV_SOLO_01"},
        # Registration pointing to non-existent event
        {"participant_id": "P_VALID_01", "event_id": "EV_GHOST"},
        # Team registration missing team_id
        {"participant_id": "P_VALID_01", "event_id": "EV_TEAM_01", "team_id": ""},
    ]
    
    issues = validate_cross_pack(
        participants=participants,
        registrations=registrations,
        events=events,
        contingents=contingents,
        vendors=vendors,
        festival_end_date="2026-11-01",
    )
    
    issue_codes = {iss.code for iss in issues}
    
    assert "UNKNOWN_PARTICIPANT_IN_REGISTRATION" in issue_codes
    assert "UNKNOWN_EVENT_IN_REGISTRATION" in issue_codes
    assert "TEAM_REGISTRATION_MISSING_TEAM_ID" in issue_codes
    assert "CONTINGENT_STRENGTH_MISMATCH" in issue_codes
    assert "HYGIENE_CERTIFICATE_EXPIRED_OR_EXPIRING" in issue_codes
