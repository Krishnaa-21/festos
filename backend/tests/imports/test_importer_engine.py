# OWNER: P2
from pathlib import Path

import pytest
from app.engines.importer import (
    MalformedCSVError,
    MissingColumnsError,
    normalizers,
    parse_csv_content,
    validate_cross_pack,
)


def test_malformed_csv_error():
    """Verify malformed CSV byte streams raise MalformedCSVError."""
    # Malformed with unclosed quotes and null bytes
    malformed_content = b'name,gender,contingent_id\n"Unclosed Name,Male,C01\n\x00corrupt'
    with pytest.raises(MalformedCSVError):
        parse_csv_content(malformed_content, "participants.csv", "participants")


def test_missing_required_columns():
    """Verify CSV with missing required columns raises MissingColumnsError with field names."""
    # Contingent mapping requires contingent_id and name
    incomplete_csv = b"declared_strength,contact_phone\n50,9876543210\n"
    with pytest.raises(MissingColumnsError) as exc_info:
        parse_csv_content(incomplete_csv, "contingents.csv", "contingents")
    assert "contingent_id" in str(exc_info.value) or "name" in str(exc_info.value)


def test_unknown_stays_unknown():
    """Verify blank or unrecognized inputs become literal UNKNOWN, never NO or NULL."""
    # Normalizers
    assert normalizers.normalize_tri_state("") == "UNKNOWN"
    assert normalizers.normalize_tri_state(None) == "UNKNOWN"
    assert normalizers.normalize_tri_state("maybe") == "UNKNOWN"
    assert normalizers.normalize_tri_state("n/a") == "UNKNOWN"
    assert normalizers.normalize_tri_state("NO") == "NO"
    assert normalizers.normalize_tri_state("YES") == "YES"

    # Gender normalizer
    assert normalizers.normalize_gender("") == "UNKNOWN"
    assert normalizers.normalize_gender("Alien") == "UNKNOWN"
    assert normalizers.normalize_gender("Non-binary") == "Non-binary"
    assert normalizers.normalize_gender("Prefer not to say") == "Prefer not to say"

    # Diet normalizer
    assert normalizers.normalize_diet("") == "UNKNOWN"
    assert normalizers.normalize_diet(None) == "UNKNOWN"
    assert normalizers.normalize_diet("unknown") == "UNKNOWN"

    # Test full row parsing preserves UNKNOWN
    csv_row = (
        b"name,gender,contingent_id,diet,accommodation_requested\n"
        b"Test User,,,,\n"
    )
    result = parse_csv_content(csv_row, "participants")
    assert len(result.staged_records) == 1
    payload = result.staged_records[0]
    assert payload["gender"] == "UNKNOWN"
    assert payload["diet"] == "UNKNOWN"
    assert payload["accommodation_requested"] == "UNKNOWN"


def test_quarantine_rows_carry_reasons():
    """Verify invalid rows (e.g. arrival >= departure) are isolated to quarantine with clear reason codes."""
    csv_data = (
        b"participant_id,name,contingent_id,arrival_time,departure_time\n"
        b"P0001,Valid Arrival,C01,2026-10-30 10:00,2026-11-02 18:00\n"
        b"P0037,Invalid Arrival,C05,2026-11-03 10:00,2026-10-30 18:00\n"
    )
    result = parse_csv_content(csv_data, "participants")
    assert len(result.staged_records) == 1
    assert result.staged_records[0]["name"] == "Valid Arrival"

    assert len(result.quarantine_records) == 1
    q_row = result.quarantine_records[0]
    assert q_row["reason_code"] == "INVALID_ARRIVAL_DEPARTURE_INTERVAL"
    assert "scheduled at or after departure" in q_row["reason"]
    assert q_row["raw_payload"]["name"] == "Invalid Arrival"



def test_raw_records_preserved_byte_for_byte():
    """Verify raw rows are stored untouched with exact field-values."""
    raw_content = b"participant_id,name,contingent_id,phone\nP0099,Raw Name  ,C02, +91 99999 88888 \n"
    result = parse_csv_content(raw_content, "participants")
    assert len(result.raw_records) == 1
    raw = result.raw_records[0]
    # Check untouched preserving raw spaces
    assert raw["raw_payload"]["name"] == "Raw Name  "
    assert raw["raw_payload"]["phone"] == " +91 99999 88888 "


def test_golden_counts_comparison():
    """Compare raw CSV data against spec reference numbers: assert plausibility and print differences."""
    raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"
    if not raw_dir.exists():
        pytest.skip("data/raw not accessible")

    # 1. Participants: spec declared 2,842 vs 2,836 actual records
    participants_path = raw_dir / "participants.csv"
    p_result = parse_csv_content(participants_path.read_bytes(), "participants")
    total_participants = p_result.total_rows
    quarantined = len(p_result.quarantine_records)
    staged = len(p_result.staged_records)

    print(f"\n[Golden Count] Participants: total={total_participants}, staged={staged}, quarantined={quarantined}")
    assert total_participants == 2836, f"Expected 2836 raw participants, found {total_participants}"
    assert quarantined == 3, f"Expected exactly 3 invalid arrival intervals, found {quarantined}"
    assert staged == 2833

    # Check the 3 quarantined participant IDs
    q_ids = [q["raw_payload"].get("participant_id") for q in p_result.quarantine_records]
    print(f"[Golden Count] Quarantined participant IDs: {q_ids}")
    assert set(q_ids) == {"P0037", "P1189", "P2034"}

    # 2. Contingents: 38 contingents, declared total 2,842
    contingents_path = raw_dir / "contingents.csv"
    c_result = parse_csv_content(contingents_path.read_bytes(), "contingents")
    assert c_result.total_rows == 38
    declared_total = sum(int(r.get("strength_declared", 0)) for r in c_result.staged_records)
    print(f"[Golden Count] Contingents: 38 rows. Declared total={declared_total} vs participants={total_participants} (Diff: {declared_total - total_participants})")
    assert declared_total == 2842

    # 3. Hostels: spec 710 beds
    hostels_path = raw_dir / "hostels.csv"
    h_result = parse_csv_content(hostels_path.read_bytes(), "hostels")
    assert h_result.total_rows == 200
    hostel_beds = sum(int(r.get("capacity", 0)) for r in h_result.staged_records)
    print(f"[Golden Count] Hostel rooms: {h_result.total_rows}, total beds={hostel_beds} (spec reference: 710)")
    assert hostel_beds == 710

    # 4. External stays: spec 740 beds across 6 properties
    external_path = raw_dir / "external_stays.csv"
    ext_result = parse_csv_content(external_path.read_bytes(), "external_stays")
    assert ext_result.total_rows == 6
    ext_beds = sum(int(r.get("beds", 0)) for r in ext_result.staged_records)
    print(f"[Golden Count] External properties: {ext_result.total_rows}, total beds={ext_beds} (spec reference: 740)")
    assert ext_beds == 740


    # 5. Cross-file validation: leader/escort presence, vendor expiry, etc.
    pack_data = {
        "participants": p_result.staged_records,
        "contingents": c_result.staged_records,
        "registrations": parse_csv_content((raw_dir / "registrations.csv").read_bytes(), "registrations").staged_records,
        "events": parse_csv_content((raw_dir / "events.csv").read_bytes(), "events").staged_records,
        "venues": parse_csv_content((raw_dir / "venues.csv").read_bytes(), "venues").staged_records,
        "hostels": h_result.staged_records,
        "external_stays": ext_result.staged_records,
        "vendors": parse_csv_content((raw_dir / "vendors.csv").read_bytes(), "vendors").staged_records,
        "inventory_logistics": parse_csv_content((raw_dir / "inventory_logistics.csv").read_bytes(), "inventory_logistics").staged_records,
    }
    issues = validate_cross_pack(pack_data)
    print(f"[Golden Count] Total cross-pack validation issues flagged: {len(issues)}")

    # Leaders/escorts: spec reference says only 3 of 38 leaders and 3 of 38 escorts in participant file
    leader_issue = next((i for i in issues if i.code == "MISSING_CONTINGENT_LEADERS"), None)
    escort_issue = next((i for i in issues if i.code == "MISSING_CONTINGENT_ESCORTS"), None)
    assert leader_issue is not None
    assert escort_issue is not None
    print(f"[Golden Count] Unresolved leaders: {leader_issue.count}/38; unresolved escorts: {escort_issue.count}/38")
    assert leader_issue.count == 35, f"Expected 35 unresolved leaders (38 - 3), found {leader_issue.count}"
    assert escort_issue.count == 35, f"Expected 35 unresolved escorts (38 - 3), found {escort_issue.count}"

    # Vendor certificate expiry: spec says 8 vendors have expired/expiring certs
    vendor_cert_issue = next((i for i in issues if i.code == "HYGIENE_CERTIFICATE_EXPIRED_OR_EXPIRING"), None)
    assert vendor_cert_issue is not None
    print(f"[Golden Count] Vendor certificate issues: {vendor_cert_issue.count}")
    assert vendor_cert_issue.count == 8, f"Expected 8 vendor cert issues, found {vendor_cert_issue.count}"


