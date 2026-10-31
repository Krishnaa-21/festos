# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AssumptionItem(BaseModel):
    id: str
    key: str
    value: str
    typed_value: Any
    type: str
    owner: str
    source: str
    reason: str
    impact_if_changed: str
    updated_at: datetime


class AssumptionUpdateRequest(BaseModel):
    key: Optional[str] = None
    value: Any
    reason: Optional[str] = "Operational baseline adjustment"
    expected_version: Optional[int] = None
    dry_run: bool = False



class AssumptionHistoryItem(BaseModel):
    change_set_id: str
    action: str = "assumptions.update"
    actor_id: str
    actor_role: str
    previous_value: Optional[str] = None
    new_value: str
    reason: Optional[str] = None
    applied_at: datetime



class AssumptionHistoryResponse(BaseModel):
    key: str
    history: List[AssumptionHistoryItem] = Field(default_factory=list)


class AssumptionDependentsResponse(BaseModel):
    key: str
    dependent_modules: List[str] = Field(default_factory=list)
    description: str
