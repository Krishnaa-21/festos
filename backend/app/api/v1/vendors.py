# OWNER: P2
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_actor
from app.models.vendors import Vendor
from app.schemas.common import Actor, Envelope

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_vendors(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    actor: Actor = Depends(get_actor),
):
    """List festival food vendors with hygiene certificate status and capacity."""
    query = select(Vendor)
    if status_filter:
        query = query.where(Vendor.status == status_filter.upper())

    all_vendors = session.exec(query).all()
    total = len(all_vendors)
    start = (page - 1) * page_size
    items = all_vendors[start : start + page_size]

    return Envelope(
        data={
            "vendors": [
                {
                    "id": v.id,
                    "name": v.name,
                    "dietary_options": v.dietary_options,
                    "menu_description": v.menu_description,
                    "hygiene_certificate_expiry": v.hygiene_certificate_expiry,
                    "hours": v.hours,
                    "capacity": v.capacity,
                    "status": v.status,
                }
                for v in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
