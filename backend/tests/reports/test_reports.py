# OWNER: P1
import io
import zipfile

import pytest
from app.core.db import get_session
from app.main import app
from app.models.audit import AuditEvent
from app.services.reports.csv_sanitizer import sanitize_csv_value, write_sanitized_csv
from app.services.reports.registry import REPORT_REGISTRY
from fastapi.testclient import TestClient
from sqlmodel import Session, select


@pytest.fixture
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


# -------------------------------------------------------------------------
# 1. Reports Catalog
# -------------------------------------------------------------------------
def test_reports_catalog_returns_all_20_reports(client: TestClient):
    """Catalog lists all 20 reports specified in Spec Section 14."""
    headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}
    res = client.get("/api/v1/reports", headers=headers)
    assert res.status_code == 200
    catalog = res.json()["data"]
    assert len(catalog) == 20

    names = [r["name"] for r in catalog]
    expected_20 = [
        "reconciliation_report.csv",
        "data_quality_report.csv",
        "accommodation_plan_A.csv",
        "accommodation_plan_B.csv",
        "accommodation_plan_C.csv",
        "shortage_report.csv",
        "accommodation_summary.csv",
        "schedule_plan.csv",
        "conflicts_report.csv",
        "unscheduled_entrants.csv",
        "inventory_plan.csv",
        "equipment_gap.csv",
        "vendor_coverage.csv",
        "vendor_compliance.csv",
        "staff_coverage.csv",
        "bed_demand_timeline.csv",
        "resource_load_timeline.csv",
        "assumptions.md",
        "incident_report.csv",
        "audit_report.csv",
    ]
    for exp in expected_20:
        assert exp in names


# -------------------------------------------------------------------------
# 2. Acceptance: All 20 Outputs Download
# -------------------------------------------------------------------------
@pytest.mark.parametrize("report_name", list(REPORT_REGISTRY.keys()))
def test_all_20_reports_download_successfully(client: TestClient, report_name: str):
    """Acceptance Test: Every single one of the 20 spec Section 14 report artifacts downloads successfully."""
    headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}
    res = client.get(f"/api/v1/reports/{report_name}", headers=headers)
    assert res.status_code == 200
    assert len(res.content) > 0
    if report_name.endswith(".csv"):
        assert "text/csv" in res.headers["content-type"]
    elif report_name.endswith(".md"):
        assert "text/markdown" in res.headers["content-type"]


# -------------------------------------------------------------------------
# 3. Bundle Zip Download
# -------------------------------------------------------------------------
def test_reports_bundle_zip(client: TestClient):
    """GET /api/v1/reports/bundle.zip returns a valid zip archive containing all authorized reports and MANIFEST.json."""
    headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}
    res = client.get("/api/v1/reports/bundle.zip", headers=headers)
    assert res.status_code == 200
    assert "application/zip" in res.headers["content-type"]

    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        namelist = zf.namelist()
        assert "MANIFEST.json" in namelist
        assert "reconciliation_report.csv" in namelist
        assert "accommodation_plan_A.csv" in namelist
        assert "assumptions.md" in namelist
        assert len(namelist) >= 21  # 20 reports + manifest


# -------------------------------------------------------------------------
# 4. CSV Injection Neutralization
# -------------------------------------------------------------------------
def test_csv_injection_neutralization():
    """Cells beginning with formula characters (=, +, -, @, \t, \r) are neutralised by prefixing with a single quote."""
    assert sanitize_csv_value("=1+1") == "'=1+1"
    assert sanitize_csv_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_value("+91-9876543210") == "'+91-9876543210"
    assert sanitize_csv_value("-5000.00") == "'-5000.00"
    assert sanitize_csv_value("Clean String") == "Clean String"
    assert sanitize_csv_value(42) == 42

    sample_rows = [
        {"name": "Alice", "payload": "=cmd|' /C calc'!A0"},
        {"name": "Bob", "payload": "@malicious_formula()"},
    ]
    csv_str = write_sanitized_csv(sample_rows)
    assert "'=cmd|" in csv_str
    assert "'@malicious_formula()" in csv_str
    assert "\n=cmd" not in csv_str


# -------------------------------------------------------------------------
# 5. Role-Based Permissions & Masking
# -------------------------------------------------------------------------
def test_role_masking_and_permission_enforcement(client: TestClient):
    """Volunteers cannot access sensitive reports and receive masked PII."""
    volunteer_headers = {"X-Actor-Role": "VOLUNTEER", "X-Actor-Id": "usr_vol"}

    # Volunteer cannot export audit report
    res_audit = client.get("/api/v1/reports/audit_report.csv", headers=volunteer_headers)
    assert res_audit.status_code == 403

    # Volunteer cannot export finance / incidents
    res_inc = client.get("/api/v1/reports/incident_report.csv", headers=volunteer_headers)
    assert res_inc.status_code == 403

    # Accommodation plan with masking hides raw phone numbers
    director_headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}
    res_plan = client.get("/api/v1/reports/accommodation_plan_A.csv?mask=true", headers=director_headers)
    assert res_plan.status_code == 200
    assert "+91-XXXXX" in res_plan.text


# -------------------------------------------------------------------------
# 6. Post-Festival Synthesis Report
# -------------------------------------------------------------------------
def test_post_festival_report_html_and_csv(client: TestClient):
    """Post-festival report generates in both HTML (executive dossier) and CSV formats."""
    headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}

    # HTML
    res_html = client.get("/api/v1/reports/post-festival?format=html", headers=headers)
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    body = res_html.text
    # Verify all 9 spec sections are present
    assert "Participant Attendance" in body
    assert "Accommodation Utilisation" in body
    assert "Event Completion" in body
    assert "Inventory & Merchandise" in body
    assert "Food Vendors & Catering" in body
    assert "Incident History" in body
    assert "Financial Expenditure" in body
    assert "Operational Delays" in body
    assert "Outstanding Settlements" in body

    # CSV
    res_csv = client.get("/api/v1/reports/post-festival?format=csv", headers=headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "section,metric,value,unit,status,notes" in res_csv.text.lower()


# -------------------------------------------------------------------------
# 7. Audit Trail on Exports
# -------------------------------------------------------------------------
def test_exports_are_audited(session: Session, client: TestClient):
    """Every report export records an audit event."""
    headers = {"X-Actor-Role": "FESTIVAL_DIRECTOR", "X-Actor-Id": "usr_dir"}
    client.get("/api/v1/reports/reconciliation_report.csv", headers=headers)

    audits = session.exec(select(AuditEvent).where(AuditEvent.entity_type == "report")).all()
    assert len(audits) >= 1
    assert any(a.action == "report.exported" for a in audits)
