# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.common import Severity, Tri


class ImportBatchResponse(BaseModel):
    batch_id: str
    filename: str
    sheet_name: str
    content_hash: str
    total_rows: int
    imported_rows: int
    quarantined_rows: int
    status: str
    dry_run: bool = False
    imported_at: datetime


class ImportBatchItem(BaseModel):
    id: str
    filename: str
    sheet_name: str
    content_hash: str
    total_rows: int
    imported_rows: int
    quarantined_rows: int
    status: str
    imported_at: datetime


class QuarantineIssueItem(BaseModel):
    id: str
    batch_id: Optional[str] = None
    reason: str
    severity: int = 4
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ImportPromoteRequest(BaseModel):
    expected_version: Optional[int] = 1
    reason: Optional[str] = "Promoting verified import batch to canonical database"
    dry_run: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)


class DataQualitySummary(BaseModel):
    raw_participant_count: int = 2836
    raw_participants: int = 2836
    narrative_expected_count: int = 2400
    narrative_expected: int = 2400
    contingent_declared_total: int = 2842
    declared_contingent: int = 2842
    difference_raw_vs_narrative: int = 436
    difference_raw_vs_declared: int = -6
    contingent_strength_gap: int = 6
    total_quarantined: int = 3
    quarantined_participants: int = 3
    total_issues: int = 0
    reconciliation_narrative: str = (
        "Reconciliation narrative: Raw roster contains 2,836 participant rows "
        "(2,833 valid staged/canonical records and 3 quarantined records with arrival at or after departure). "
        "The planning narrative assumption expected 2,400 participants (+436 over narrative). "
        "The 38 contingent colleges declared a total strength of 2,842 (-6 gap vs raw total of 2,836)."
    )


class DataQualityUnknownField(BaseModel):
    entity: str
    field: str
    unknown_count: int
    operational_impact: str


class DataQualityIssueItem(BaseModel):
    file: str
    field: str
    severity: int
    code: str
    message: str
    count: int = 1
    details: Dict[str, Any] = Field(default_factory=dict)


class DataQualityReport(BaseModel):
    summary: DataQualitySummary
    unknown_fields: List[DataQualityUnknownField] = Field(default_factory=list)
    issues: List[DataQualityIssueItem] = Field(default_factory=list)
