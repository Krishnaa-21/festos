# OWNER: P2
from pathlib import Path
import pytest
from sqlmodel import Session, select

from app.models.change import ChangeSet
from app.models.ops import ImportBatchMetadata, StagedRecord
from app.models.participants import ImportBatch, Participant, QuarantineRow, RawRecord
from app.schemas.common import Actor, Role
from app.services.assumptions.service import seed_all_assumptions
from app.services.imports.service import (
    export_data_quality_report_csv,
    generate_data_quality_report,
    get_import_batch,
    get_quarantine_issues,
    import_file,
    list_import_batches,
    promote_import_batch,
)


@pytest.fixture
def actor():
    return Actor(id="usr_director", name="Festival Director", role=Role.FESTIVAL_DIRECTOR.value)


def test_import_and_promote_pipeline(session: Session, actor: Actor):
    """Test full import pipeline: upload -> raw_record -> staging -> quarantine -> promote."""
    raw_dir = Path("/home/krishna/festos/data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not accessible")

    # Ingest participants
    p_content = (raw_dir / "participants.csv").read_bytes()
    resp = import_file(
        session=session,
        file_content=p_content,
        filename="participants.csv",
        sheet_name="participants",
        actor=actor,
    )
    assert resp.total_rows == 2836
    assert resp.imported_rows == 2833
    assert resp.quarantined_rows == 3
    assert resp.status == "STAGED"

    # Verify database state in staging
    raw_count = len(session.exec(select(RawRecord)).all())
    assert raw_count == 2836

    staged_count = len(session.exec(select(StagedRecord)).all())
    assert staged_count == 2833

    quarantine_count = len(session.exec(select(QuarantineRow)).all())
    assert quarantine_count == 3

    # Promote batch to canonical tables
    res = promote_import_batch(session, resp.batch_id, actor=actor)
    assert res.success

    # Verify canonical participants
    canonical_p = session.exec(select(Participant)).all()
    assert len(canonical_p) == 2833

    # Verify ChangeSet recorded
    cs = session.exec(select(ChangeSet).where(ChangeSet.action == "imports.promote")).first()
    assert cs is not None
    assert cs.entity_id == resp.batch_id
    assert cs.payload["promoted_count"] == 2833


def test_idempotent_reimport(session: Session, actor: Actor):
    """Verify re-importing the same content is idempotent and does not duplicate records."""
    csv_data = (
        b"contingent_id,name,declared_strength,contact_phone\n"
        b"C99,Test College,50,9876543210\n"
    )
    resp1 = import_file(session, csv_data, "contingents.csv", "contingents", actor=actor)
    assert resp1.imported_rows == 1

    # Re-import identical content
    resp2 = import_file(session, csv_data, "contingents.csv", "contingents", actor=actor)
    assert resp2.batch_id == resp1.batch_id
    assert resp2.content_hash == resp1.content_hash

    # Ensure no duplicates in raw_record or staged_record
    batches = session.exec(select(ImportBatch)).all()
    assert len(batches) == 1
    raw = session.exec(select(RawRecord)).all()
    assert len(raw) == 1


def test_dry_run_import(session: Session, actor: Actor):
    """Verify dry-run mode previews counts without committing records."""
    csv_data = (
        b"contingent_id,name,declared_strength\n"
        b"C99,Dry Run College,20\n"
    )
    resp = import_file(session, csv_data, "contingents.csv", "contingents", dry_run=True, actor=actor)
    assert resp.dry_run is True
    assert resp.imported_rows == 1

    # Database should be empty of persisted records
    batches = session.exec(select(ImportBatch)).all()
    assert len(batches) == 0
    staged = session.exec(select(StagedRecord)).all()
    assert len(staged) == 0


def test_data_quality_report_and_export(session: Session, actor: Actor):
    """Verify data-quality report accurately explains the 2,836 vs 2,400 vs 2,842 situation and unknown metrics."""
    seed_all_assumptions(session)
    raw_dir = Path("/home/krishna/festos/data/raw")
    if not raw_dir.exists():
        pytest.skip("data/raw not accessible")

    # Import contingents and participants
    c_resp = import_file(session, (raw_dir / "contingents.csv").read_bytes(), "contingents.csv", actor=actor)
    promote_import_batch(session, c_resp.batch_id, actor=actor)

    p_resp = import_file(session, (raw_dir / "participants.csv").read_bytes(), "participants.csv", actor=actor)
    promote_import_batch(session, p_resp.batch_id, actor=actor)

    report = generate_data_quality_report(session)
    assert report.summary.raw_participants == 2836
    assert report.summary.narrative_expected == 2400
    assert report.summary.declared_contingent == 2842
    assert report.summary.quarantined_participants == 3
    assert report.summary.contingent_strength_gap == 6

    # Verify reconciliation narrative is present
    assert "2,836" in report.summary.reconciliation_narrative
    assert "2,400" in report.summary.reconciliation_narrative
    assert "2,842" in report.summary.reconciliation_narrative

    # Verify unknown fields are tracked
    field_names = {u.field for u in report.unknown_fields}
    assert "gender" in field_names
    assert "diet" in field_names
    assert "accommodation_requested" in field_names

    # Test CSV export
    csv_text = export_data_quality_report_csv(session)
    assert "RECONCILIATION SUMMARY" in csv_text
    assert "UNKNOWN / MISSING FIELDS BREAKDOWN" in csv_text
    assert "DATA QUALITY ISSUES" in csv_text
