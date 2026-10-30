# OWNER: P1
from __future__ import annotations

from typing import Any, Dict, List

from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.services.reports.service import (
    generate_post_festival_report,
    generate_reports_bundle,
    generate_single_report,
    get_reports_catalog,
)
from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=Envelope[List[Dict[str, Any]]], status_code=status.HTTP_200_OK)
def list_reports(
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Envelope[List[Dict[str, Any]]]:
    """Returns the catalog of all 20 spec Section 14 reports with access permissions and metadata."""
    catalog = get_reports_catalog(session, actor)
    return Envelope(
        data=catalog,
        meta={"total_reports": len(catalog)},
        warnings=[],
    )


@router.get("/bundle.zip", status_code=status.HTTP_200_OK)
def download_reports_bundle(
    mask: bool = Query(default=True, description="Enforce role-based masking on sensitive columns"),
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Response:
    """Generates and downloads a zip archive containing all reports authorized for the caller."""
    zip_bytes = generate_reports_bundle(session, actor, mask)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="festos_reports_bundle.zip"',
            "Content-Type": "application/zip",
        },
    )


@router.get("/post-festival", status_code=status.HTTP_200_OK)
def get_post_festival_summary(
    format: str = Query(default="html", description="Output format: 'html' or 'csv'"),
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Response:
    """Generates the post-festival comprehensive operational report from live state and cryptographic audit history."""
    content, content_type = generate_post_festival_report(session, actor, format_type=format)
    headers = {}
    if format.lower() == "csv":
        headers["Content-Disposition"] = 'attachment; filename="festos_post_festival_report.csv"'

    return Response(
        content=content,
        media_type=content_type,
        headers=headers,
    )


@router.get("/{name}", status_code=status.HTTP_200_OK)
def download_report(
    name: str,
    mask: bool = Query(default=True, description="Enforce role-based masking on sensitive columns"),
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Response:
    """Generates and downloads a single spec report by name (e.g. reconciliation_report.csv)."""
    content, content_type, filename = generate_single_report(name, session, actor, mask)
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": content_type,
        },
    )
