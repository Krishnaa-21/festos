# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.db import get_session
from app.core.deps import require_permission
from app.schemas.common import Actor, Envelope
from app.schemas.vendors import (
    VendorDetailSchema,
    VendorShutdownAnalysisRequest,
    VendorShutdownAnalysisResult,
    VendorShutdownExecuteRequest,
)
from app.services.vendors.service import (
    execute_shutdown,
    generate_vendor_compliance_csv,
    generate_vendor_coverage_csv,
    get_vendor_compliance_overview,
    get_vendor_detail,
    list_vendors,
    simulate_shutdown_impact,
)
from fastapi import APIRouter, Depends, Header, Query, Response
from sqlmodel import Session

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_vendors_endpoint(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, SUSPENDED, SHUT_DOWN)"),
    dietary_option: Optional[str] = Query(None, description="Filter by declared dietary option"),
    compliance_status: Optional[str] = Query(None, description="Filter by validity (VALID_THROUGHOUT, EXPIRES_DURING_FESTIVAL, EXPIRED)"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:read")),
):
    """List all 14 commercial catering vendors with operating details and compliance status."""
    res = list_vendors(
        session=session,
        status=status,
        dietary_option=dietary_option,
        compliance_status=compliance_status,
    )
    return Envelope(data=res)


@router.get("/compliance", response_model=Envelope[Dict[str, Any]])
def get_compliance_endpoint(
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:read")),
):
    """Return vendor hygiene certificate compliance breakdown and menu-label mismatches."""
    res = get_vendor_compliance_overview(session)
    return Envelope(data=res)


@router.get("/reports/{report_name}")
def download_vendor_report_endpoint(
    report_name: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:read")),
):
    """Download vendor coverage or compliance reports as CSV."""
    if "coverage" in report_name.lower():
        content = generate_vendor_coverage_csv(session)
        filename = "vendor_coverage.csv"
    elif "compliance" in report_name.lower():
        content = generate_vendor_compliance_csv(session)
        filename = "vendor_compliance.csv"
    else:
        content = generate_vendor_compliance_csv(session)
        filename = "vendor_report.csv"

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{id}", response_model=Envelope[VendorDetailSchema])
def get_vendor_detail_endpoint(
    id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:read")),
):
    """Get detailed profile for a specific vendor including menu items, assignments, and flags."""
    res = get_vendor_detail(session, id)
    return Envelope(data=res)


@router.post("/{id}/shutdown-impact", response_model=Envelope[VendorShutdownAnalysisResult])
@router.post("/{id}/shutdown-analysis", response_model=Envelope[VendorShutdownAnalysisResult])
def shutdown_impact_endpoint(
    id: str,
    body: Optional[VendorShutdownAnalysisRequest] = None,
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:write")),
):
    """Evaluate the 10-step emergency vendor shutdown response (Feature 7)."""
    req = body or VendorShutdownAnalysisRequest()
    res = simulate_shutdown_impact(session=session, vendor_id=id, req=req)
    return Envelope(data=res)


@router.post("/{id}/shutdown", response_model=Envelope[Dict[str, Any]])
@router.post("/{id}/shutdown-execute", response_model=Envelope[Dict[str, Any]])
def execute_shutdown_endpoint(
    id: str,
    body: VendorShutdownExecuteRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(require_permission("vendors:write")),
):
    """Execute emergency vendor shutdown via ChangeService, reassigning slots and staging notification drafts."""
    res = execute_shutdown(
        session=session,
        vendor_id=id,
        req=body,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    return Envelope(data=res)
