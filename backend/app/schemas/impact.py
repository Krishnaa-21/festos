# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ImpactNode(BaseModel):
    id: str
    type: str  # participant, room, hostel, event, venue, vendor, equipment, etc.
    label: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    severity: str = "MEDIUM"  # CRITICAL | HIGH | MEDIUM | LOW
    people_affected: int = 0
    depth: int = 0
    update_status: str = "PENDING"  # PENDING | UPDATED | VERIFIED
    reason: Optional[str] = None
    children: List[ImpactNode] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        if not self.entity_type:
            self.entity_type = self.type
        if not self.entity_id:
            self.entity_id = self.id


class ImpactAnalyzeRequest(BaseModel):
    entity_type: str
    entity_id: str
    action: str = "disrupt"
    reason: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    max_depth: int = 5

    @property
    def effective_payload(self) -> Dict[str, Any]:
        return self.payload if self.payload is not None else self.parameters


class ImpactReport(BaseModel):
    root_entity: Dict[str, Any]
    tree: ImpactNode
    counts_by_type: Dict[str, int] = Field(default_factory=dict)
    severities: Dict[str, int] = Field(default_factory=dict)
    total_people_affected: int = 0
    recommendations: List[str] = Field(default_factory=list)
    before_after_comparison: Dict[str, Any] = Field(default_factory=dict)
    nodes_flat: List[Dict[str, Any]] = Field(default_factory=list)


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    severity: str = "LOW"
    people_affected: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class ImpactGraphResponse(BaseModel):
    entity: str
    direct_dependents: List[Dict[str, Any]] = Field(default_factory=list)
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
