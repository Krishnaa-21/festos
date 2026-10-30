# OWNER: P1
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.core.clock import now


class DecisionCard(SQLModel, table=True):
    __tablename__ = "decision_card"

    id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:8]}", primary_key=True)
    module: str = Field(index=True)  # accommodation|schedule|vendors|incidents|overrides|logistics
    decision_type: str = Field(index=True)
    title: str = Field(index=True)
    summary: str
    why: str
    hard_constraints_satisfied: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    soft_constraints_relaxed: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    alternatives_rejected: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    cost_impact_inr: float = Field(default=0.0)
    people_affected: int = Field(default=0)
    approved_by: Optional[str] = Field(default=None, index=True)
    approved_at: datetime = Field(default_factory=now, index=True)
    override_id: Optional[str] = Field(default=None, foreign_key="override.id", index=True)
    entity_refs: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=now)
