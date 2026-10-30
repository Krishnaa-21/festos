# OWNER: P2
from typing import Optional

from app.core.db import get_session
from app.core.deps import get_actor
from app.schemas.common import Actor, Envelope
from app.schemas.imports import DataQualityReport
from app.services.imports.service import (
    export_data_quality_report_csv,
    generate_data_quality_report,
)
from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("", response_model=Envelope[DataQualityReport])
def get_data_quality(
    format: Optional[str] = Query(None, description="Set to 'csv' for exportable data_quality_report.csv"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Retrieves comprehensive data quality report:
    - Reconciliation shell summary (2,836 raw vs 2,400 narrative vs 2,842 declared)
    - Counts of UNKNOWN per field with operational impact
    - List of detected anomalies and validation issues across all files
    """
    if format and format.lower() == "csv":
        csv_data = export_data_quality_report_csv(session)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=data_quality_report.csv"},
        )

    report = generate_data_quality_report(session)
    return Envelope(data=report)
