# OWNER: P2
from typing import Any, Dict, List, Optional

from app.core.db import get_session
from app.core.deps import get_actor
from app.core.rbac import check_permission
from app.schemas.common import Actor, Envelope
from app.schemas.incidents import (
    ApprovePlanRequest,
    DisruptionCatalogResponse,
    IncidentDetailSchema,
    InjectIncidentRequest,
    RecoveryPlanSchema,
    VerifyIncidentResponse,
)
from app.services.incidents.service import (
    approve_incident_plan,
    generate_incident_report_csv,
    get_disruption_catalog,
    get_incident,
    inject_incident,
)
from app.services.incidents.service import (
    list_incidents as list_incidents_service,
)
from app.services.incidents.service import (
    verify_incident as verify_incident_service,
)
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlmodel import Session

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/catalog", response_model=Envelope[DisruptionCatalogResponse])
def get_catalog(
    actor: Actor = Depends(get_actor),
):
    """Return catalog of 7 mandatory disruption scenarios + extras with schemas (Spec 12.5)."""
    check_permission(actor, "incidents:read")
    catalog = get_disruption_catalog()
    return Envelope(data=catalog)


@router.get("/report/csv")
def download_incident_report_csv(
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Download comprehensive incident_report.csv (Task 7)."""
    check_permission(actor, "incidents:read")
    csv_data = generate_incident_report_csv(session)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="incident_report.csv"'},
    )


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    scenario_type: Optional[str] = Query(None),
    severity: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List operational incidents with filters (Task 7)."""
    check_permission(actor, "incidents:read")
    all_items = list_incidents_service(
        session=session,
        status_filter=status_filter,
        scenario_type=scenario_type,
        severity=severity,
    )
    total = len(all_items)
    start = (page - 1) * page_size
    items = all_items[start : start + page_size]

    return Envelope(
        data={
            "items": [
                {
                    "id": inc.id,
                    "scenario_type": inc.scenario_type,
                    "title": inc.title,
                    "severity": inc.severity,
                    "category": inc.category,
                    "description": inc.description,
                    "status": inc.status,
                    "reported_by": inc.reported_by,
                    "reported_at": inc.reported_at.isoformat() if inc.reported_at else None,
                    "people_affected": inc.people_affected,
                    "recovery_plans_count": len(inc.plans) if inc.plans else 0,
                    "approved_plan_id": inc.approved_plan_id,
                    "decision_card_id": inc.decision_card_id,
                }
                for inc in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("", response_model=Envelope[Dict[str, Any]], status_code=status.HTTP_201_CREATED)
def create_or_inject_incident(
    req: InjectIncidentRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Inject a disruption incident, compute blast radius, and generate recovery plans (Task 2 & 3)."""
    check_permission(actor, "incidents:write")
    result = inject_incident(session=session, req=req, actor=actor)
    return Envelope(data=result)


@router.get("/{incident_id}", response_model=Envelope[IncidentDetailSchema])
def get_incident_detail(
    incident_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Get full incident details with timeline and recovery plan summary (Task 7)."""
    check_permission(actor, "incidents:read")
    inc = get_incident(session, incident_id)
    return Envelope(
        data=IncidentDetailSchema(
            id=inc.id,
            scenario_type=inc.scenario_type,
            title=inc.title,
            severity=str(inc.severity),
            category=inc.category,
            description=inc.description,
            status=inc.status,
            reported_by=inc.reported_by,
            reported_at=inc.reported_at.isoformat() if inc.reported_at else "",
            timeline=inc.timeline,
            impact_summary=inc.impact_summary,
            recovery_plans_count=len(inc.plans) if inc.plans else 0,
            approved_plan_id=inc.approved_plan_id,
            change_set_id=inc.change_set_id,
            decision_card_id=inc.decision_card_id,
            verified_at=inc.verified_at.isoformat() if inc.verified_at else None,
            people_affected=inc.people_affected,
            concurrent_conflicts=inc.concurrent_conflicts,
        )
    )


@router.get("/{incident_id}/impact", response_model=Envelope[Dict[str, Any]])
def get_incident_impact(
    incident_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Get incident impact tree and blast radius comparison (Task 7)."""
    check_permission(actor, "incidents:read")
    inc = get_incident(session, incident_id)
    return Envelope(
        data={
            "incident_id": inc.id,
            "scenario_type": inc.scenario_type,
            "people_affected": inc.people_affected,
            "impact_summary": inc.impact_summary,
            "impact_tree": inc.impact_tree,
        }
    )


@router.get("/{incident_id}/plans", response_model=Envelope[List[RecoveryPlanSchema]])
def get_incident_plans(
    incident_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Get ranked candidate recovery plans for an incident (Task 7)."""
    check_permission(actor, "incidents:read")
    inc = get_incident(session, incident_id)
    return Envelope(data=inc.plans or [])


@router.post("/{incident_id}/approve", response_model=Envelope[IncidentDetailSchema])
def approve_plan(
    incident_id: str,
    req: ApprovePlanRequest,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Approve a recovery plan, execute real mutations, write ChangeSet & DecisionCard (Task 3 & 7)."""
    check_permission(actor, "incidents:write")
    inc = approve_incident_plan(session, incident_id, req, actor)
    return Envelope(
        data=IncidentDetailSchema(
            id=inc.id,
            scenario_type=inc.scenario_type,
            title=inc.title,
            severity=str(inc.severity),
            category=inc.category,
            description=inc.description,
            status=inc.status,
            reported_by=inc.reported_by,
            reported_at=inc.reported_at.isoformat() if inc.reported_at else "",
            timeline=inc.timeline,
            impact_summary=inc.impact_summary,
            recovery_plans_count=len(inc.plans) if inc.plans else 0,
            approved_plan_id=inc.approved_plan_id,
            change_set_id=inc.change_set_id,
            decision_card_id=inc.decision_card_id,
            verified_at=inc.verified_at.isoformat() if inc.verified_at else None,
            people_affected=inc.people_affected,
            concurrent_conflicts=inc.concurrent_conflicts,
        )
    )


@router.post("/{incident_id}/verify", response_model=Envelope[VerifyIncidentResponse])
def verify_incident(
    incident_id: str,
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """Verify post-recovery state, mark nodes VERIFIED, and close incident (Task 3 & 7)."""
    check_permission(actor, "incidents:write")
    resp = verify_incident_service(session, incident_id, actor)
    return Envelope(data=resp)
