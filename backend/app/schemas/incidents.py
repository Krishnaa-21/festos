# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DisruptionScenarioInfo(BaseModel):
    scenario_type: str
    title: str
    description: str
    target_domain: str
    parameters_schema: Dict[str, Any]


class DisruptionCatalogResponse(BaseModel):
    scenarios: List[DisruptionScenarioInfo]


class InjectIncidentRequest(BaseModel):
    scenario_type: str
    title: Optional[str] = None
    severity: Optional[str] = "HIGH"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
    reason: Optional[str] = None


class IncidentTimelineEvent(BaseModel):
    status: str
    timestamp: str
    actor: str
    notes: Optional[str] = None


class RecoveryPlanSchema(BaseModel):
    plan_id: str
    rank: int
    name: str
    summary: str
    people_moved: int
    schedule_changes: int
    resource_moves: int
    cost_increase_inr: float
    cohesion_score: float
    changes_count: int
    notifications_drafted: int
    requires_director_approval: bool
    change_set_payload: Dict[str, Any] = Field(default_factory=dict)
    notification_draft_ids: List[str] = Field(default_factory=list)


class IncidentDetailSchema(BaseModel):
    id: str
    scenario_type: Optional[str] = None
    title: str
    severity: str
    category: str
    description: str
    status: str
    reported_by: str
    reported_at: str
    timeline: List[IncidentTimelineEvent] = Field(default_factory=list)
    impact_summary: Dict[str, Any] = Field(default_factory=dict)
    recovery_plans_count: int = 0
    approved_plan_id: Optional[str] = None
    change_set_id: Optional[str] = None
    decision_card_id: Optional[str] = None
    verified_at: Optional[str] = None
    people_affected: int = 0
    concurrent_conflicts: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovePlanRequest(BaseModel):
    plan_id: str
    reason: str


class VerifyIncidentResponse(BaseModel):
    incident_id: str
    status: str
    verified_at: str
    verification_passed: bool
    remaining_risks: List[Dict[str, Any]] = Field(default_factory=list)
    before_after: Dict[str, Any] = Field(default_factory=dict)
    decision_card_id: Optional[str] = None
