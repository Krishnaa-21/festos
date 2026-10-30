# OWNER: P1
from typing import Any, Dict, List, Optional

from app.core.change_service import ChangeHandler, ChangeRequest, ChangeResult, execute_change
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.registry import register_change_handler
from app.schemas.common import Actor, Envelope, Severity, Violation
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlmodel import Session

router = APIRouter(prefix="/_example", tags=["Example Flow"])

# -------------------------------------------------------------
# 1. PURE ENGINE: pure logic, zero DB/FastAPI dependencies
# -------------------------------------------------------------
def compute_welcome_pack_score(participant_role: str, age: Optional[int]) -> int:
    """Pure domain calculation."""
    score = 10
    if participant_role in ["LEADER", "ESCORT"]:
        score += 5
    if age and age < 18:
        score += 2
    return score

# -------------------------------------------------------------
# 2. CHANGE HANDLER: validate, snapshot, apply, risk
# -------------------------------------------------------------
@register_change_handler("example.create_item")
class ExampleCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        violations = []
        name = req.payload.get("name")
        if not name or len(name.strip()) < 3:
            violations.append(
                Violation(
                    code="NAME_TOO_SHORT",
                    severity=Severity.HIGH,
                    hard=True,
                    message="Item name must be at least 3 characters",
                    entity_refs=[]
                )
            )
        return violations

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {"exists": False, "version": 0}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        # Engine call inside handler
        score = compute_welcome_pack_score(
            participant_role=req.payload.get("role", "PARTICIPANT"),
            age=req.payload.get("age")
        )
        return {
            "entity_id": req.entity_id,
            "name": req.payload.get("name"),
            "score": score,
            "status": "CREATED"
        }

    def risk(self, req: ChangeRequest) -> str:
        if req.payload.get("is_high_risk"):
            return "HIGH"
        return "LOW"

# -------------------------------------------------------------
# 3. SERVICE LAYER: orchestrates ChangeRequest -> ChangeService
# -------------------------------------------------------------
def create_example_item(
    item_id: str,
    name: str,
    role: str,
    age: Optional[int],
    is_high_risk: bool,
    actor: Actor,
    session: Session,
    reason: Optional[str] = None,
    dry_run: bool = False,
    expected_version: Optional[int] = None
) -> ChangeResult:
    req = ChangeRequest(
        action="example.create_item",
        entity_type="example_item",
        entity_id=item_id,
        payload={"name": name, "role": role, "age": age, "is_high_risk": is_high_risk},
        reason=reason,
        actor=actor,
        dry_run=dry_run,
        expected_version=expected_version
    )
    return execute_change(req, session)

# -------------------------------------------------------------
# 4. ROUTER LAYER: thin presentation unrolling into Envelope
# -------------------------------------------------------------
class CreateExampleRequest(BaseModel):
    id: str = Field(..., description="Unique ID for item")
    name: str = Field(..., description="Item name")
    role: str = Field(default="PARTICIPANT")
    age: Optional[int] = None
    is_high_risk: bool = False
    reason: Optional[str] = None
    dry_run: bool = False
    expected_version: Optional[int] = None

@router.post("/items", response_model=Envelope[ChangeResult])
def post_create_example_item(
    body: CreateExampleRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    result = create_example_item(
        item_id=body.id,
        name=body.name,
        role=body.role,
        age=body.age,
        is_high_risk=body.is_high_risk,
        actor=actor,
        session=session,
        reason=body.reason,
        dry_run=body.dry_run,
        expected_version=body.expected_version
    )
    return Envelope(
        data=result,
        meta={"actor": actor.name, "idempotency_key": idempotency_key},
        warnings=result.warnings
    )
