# OWNER: P1
from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

Tri = Literal["YES", "NO", "UNKNOWN"]

class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Role(str, Enum):
    FESTIVAL_DIRECTOR = "FESTIVAL_DIRECTOR"
    ACCOMMODATION_LEAD = "ACCOMMODATION_LEAD"
    EVENT_LEAD = "EVENT_LEAD"
    LOGISTICS_MANAGER = "LOGISTICS_MANAGER"
    MERCHANDISE_MANAGER = "MERCHANDISE_MANAGER"
    FOOD_OPS_MANAGER = "FOOD_OPS_MANAGER"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    VOLUNTEER = "VOLUNTEER"
    AUDITOR = "AUDITOR"

class EntityRef(BaseModel):
    type: str
    id: str
    label: str

class Actor(BaseModel):
    id: str
    name: str
    role: str
    contingent_id: Optional[str] = None

class Violation(BaseModel):
    code: str
    severity: Severity = Severity.MEDIUM
    hard: bool = True
    message: str
    entity_refs: List[EntityRef] = Field(default_factory=list)

class ActionRef(BaseModel):
    label: str
    route: str
    api: str

class RiskItem(BaseModel):
    id: str
    module: str
    kind: str
    title: str
    severity: Severity
    hours_to_impact: Optional[float] = None
    people_affected: int = 0
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    resource_criticality: int = Field(default=1, ge=1, le=5)
    entity_refs: List[EntityRef] = Field(default_factory=list)
    action: Optional[ActionRef] = None
    explanation: str = ""

class ImpactNode(BaseModel):
    type: str
    id: str
    label: str
    severity: Severity = Severity.LOW
    people_affected: int = 0
    depth: int = 0
    parent: Optional[str] = None
    status: str = "AFFECTED"

class ImpactReport(BaseModel):
    root_change: dict[str, Any]
    nodes: List[ImpactNode] = Field(default_factory=list)
    counts_by_type: dict[str, int] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    before_after: dict[str, Any] = Field(default_factory=dict)

class SoftRelaxed(BaseModel):
    constraint: str
    reason: str

class AlternativeRejected(BaseModel):
    option: str
    why: str

class DecisionCard(BaseModel):
    id: str
    subject: str
    recommendation: str
    hard_satisfied: bool = True
    soft_relaxed: List[SoftRelaxed] = Field(default_factory=list)
    alternatives_rejected: List[AlternativeRejected] = Field(default_factory=list)
    cost_impact: Optional[float] = None
    people_affected: int = 0
    approved_by: Optional[str] = None
    created_at: datetime

T = TypeVar("T")

class Envelope(BaseModel, Generic[T]):
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> Page[T]:
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None
    request_id: Optional[str] = None

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
