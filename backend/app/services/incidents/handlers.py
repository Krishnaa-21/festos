# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List

from sqlmodel import Session

from app.core.change_service import ChangeHandler, ChangeRequest
from app.core.registry import register_change_handler
from app.models.ops import Incident
from app.schemas.common import Violation
from app.schemas.incidents import ApprovePlanRequest, InjectIncidentRequest
from app.services.incidents.service import approve_incident_plan, inject_incident, verify_incident


@register_change_handler("incident.create")
class IncidentCreateHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        return {}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        inject_req = InjectIncidentRequest(
            scenario_type=req.payload.get("scenario_type", "GENERIC_DISRUPTION"),
            title=req.payload.get("title"),
            severity=req.payload.get("severity", "HIGH"),
            entity_type=req.payload.get("entity_type") or req.entity_type,
            entity_id=req.payload.get("entity_id") or req.entity_id,
            parameters=req.payload.get("parameters", {}),
            dry_run=req.dry_run,
            reason=req.reason,
        )
        res = inject_incident(session, inject_req, req.actor)
        return res


@register_change_handler("incident.approve_plan")
class IncidentApprovePlanHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        plan_id = req.payload.get("plan_id")
        if not plan_id:
            return [Violation(code="MISSING_FIELD", message="plan_id is required", path="plan_id", hard=True)]
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        inc = session.get(Incident, req.entity_id)
        return {"status": inc.status if inc else "UNKNOWN"}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        approve_req = ApprovePlanRequest(
            plan_id=req.payload["plan_id"],
            reason=req.reason or req.payload.get("reason", "Approved recovery plan"),
        )
        inc = approve_incident_plan(session, req.entity_id, approve_req, req.actor)
        return {
            "incident_id": inc.id,
            "status": inc.status,
            "approved_plan_id": inc.approved_plan_id,
            "change_set_id": inc.change_set_id,
            "decision_card_id": inc.decision_card_id,
        }


@register_change_handler("incident.verify")
class IncidentVerifyHandler(ChangeHandler):
    def validate(self, req: ChangeRequest, session: Session) -> List[Violation]:
        return []

    def snapshot(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        inc = session.get(Incident, req.entity_id)
        return {"status": inc.status if inc else "UNKNOWN"}

    def apply(self, req: ChangeRequest, session: Session) -> Dict[str, Any]:
        res = verify_incident(session, req.entity_id, req.actor)
        return res.model_dump()
