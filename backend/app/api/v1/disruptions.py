# OWNER: P2
from app.core.deps import get_actor
from app.core.rbac import check_permission
from app.schemas.common import Actor, Envelope
from app.schemas.incidents import DisruptionCatalogResponse
from app.services.incidents.service import get_disruption_catalog
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/disruptions", tags=["disruptions"])


@router.get("/catalog", response_model=Envelope[DisruptionCatalogResponse])
def get_catalog(
    actor: Actor = Depends(get_actor),
):
    """Return catalog of 7 mandatory disruption scenarios + extras with schemas (Spec 12.5)."""
    check_permission(actor, "incidents:read")
    catalog = get_disruption_catalog()
    return Envelope(data=catalog)
