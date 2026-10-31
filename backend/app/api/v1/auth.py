# OWNER: P3
import uuid
from datetime import timedelta
from typing import Any, Dict

import app.core.audit as audit_module
from app.core.clock import now
from app.core.db import get_session
from app.core.config import settings
from app.core.deps import get_actor
from app.core.errors import FestOSError, RateLimitedError, UnauthenticatedError
from app.core.rbac import get_all_permissions_matrix, get_role_permissions
from app.core.security import (
    LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_ATTEMPTS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_password,
)
from app.models.audit import BreakGlassGrant, User
from app.schemas.common import Actor, Envelope, Role
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class BreakGlassRequest(BaseModel):
    entity: str = Field(..., description="Target entity identifier, e.g., participant:P10023")
    field: str = Field(..., description="Sensitive field name, e.g., medical_notes")
    reason: str = Field(..., description="Mandatory operational or emergency rationale")
    minutes: int = Field(default=15, ge=1, le=60, description="Grant TTL in minutes (max 60)")


@router.post("/login", response_model=Envelope[Dict[str, Any]])
def post_login(
    body: LoginRequest,
    session: Session = Depends(get_session)
):
    """Authenticate with email and password. Returns access and refresh JWT tokens."""
    user = session.exec(select(User).where(User.email == body.email.strip().lower())).first()
    if not user:
        raise UnauthenticatedError("Invalid email or password")

    if not user.is_active:
        raise UnauthenticatedError("User account has been deactivated")

    # Check lockout
    if user.locked_until and user.locked_until > now():
        raise RateLimitedError(
            f"Account is temporarily locked due to excessive failed attempts. Please wait until {user.locked_until.isoformat()}."
        )

    if not verify_password(body.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        session.add(user)
        session.commit()
        raise UnauthenticatedError("Invalid email or password")

    # Reset lockout counters on success
    user.failed_login_attempts = 0
    user.locked_until = None
    session.add(user)
    session.commit()

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "contingent_id": user.contingent_id
    })
    refresh_token = create_refresh_token(user.id)

    return Envelope(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_MIN * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "contingent_id": user.contingent_id
            }
        }
    )


@router.post("/refresh", response_model=Envelope[Dict[str, Any]])
def post_refresh(
    body: RefreshRequest,
    session: Session = Depends(get_session)
):
    """Obtain a new access token using a valid refresh token."""
    payload = decode_access_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthenticatedError("Invalid or expired refresh token")

    user_id = payload.get("sub")
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise UnauthenticatedError("User account is inactive or not found")

    new_access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "contingent_id": user.contingent_id
    })

    return Envelope(
        data={
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_MIN * 60
        }
    )


@router.get("/me", response_model=Envelope[Dict[str, Any]])
def get_me(
    actor: Actor = Depends(get_actor)
):
    """Retrieve profile and permissions for the current authenticated user."""
    perms = get_role_permissions(actor.role)
    return Envelope(
        data={
            "id": actor.id,
            "name": actor.name,
            "role": actor.role,
            "contingent_id": actor.contingent_id,
            "permissions": perms
        }
    )


@router.get("/permissions", response_model=Envelope[Dict[str, Any]])
def get_permissions():
    """Retrieve full RBAC permission matrix for all festival roles."""
    matrix = get_all_permissions_matrix()
    return Envelope(
        data={
            "roles": matrix
        }
    )


@router.post("/break-glass", response_model=Envelope[Dict[str, Any]])
def post_break_glass(
    body: BreakGlassRequest,
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session)
):
    """Request temporary unmasking of a sensitive entity field. Requires mandatory reason and logs to audit."""
    if not body.reason or not body.reason.strip():
        raise FestOSError(
            message="A recorded operational reason is strictly mandatory for emergency break-glass elevation.",
            code="VALIDATION_ERROR",
            status_code=422
        )

    grant_id = f"bgg_{uuid.uuid4().hex[:8]}"
    expires_at = now() + timedelta(minutes=body.minutes)

    grant = BreakGlassGrant(
        id=grant_id,
        user_id=actor.id,
        entity=body.entity.strip(),
        field=body.field.strip(),
        reason=body.reason.strip(),
        granted_by=actor.name or actor.id,
        expires_at=expires_at,
        is_revoked=False,
        created_at=now()
    )
    session.add(grant)
    session.flush()

    audit_id = audit_module.record(
        session=session,
        actor=actor,
        action="auth.break_glass_granted",
        entity_type="break_glass_grant",
        entity_id=grant_id,
        before={},
        after={
            "grant_id": grant_id,
            "entity": grant.entity,
            "field": grant.field,
            "reason": grant.reason,
            "expires_at": grant.expires_at.isoformat()
        },
        reason=body.reason.strip(),
        status="SUCCESS"
    )

    session.commit()

    return Envelope(
        data={
            "grant_id": grant.id,
            "user_id": grant.user_id,
            "entity": grant.entity,
            "field": grant.field,
            "reason": grant.reason,
            "expires_at": grant.expires_at.isoformat(),
            "created_at": grant.created_at.isoformat(),
            "audit_event_id": audit_id
        },
        warnings=["Break-glass emergency access granted. This action is permanently recorded in the immutable audit log."]
    )


@router.get("/break-glass", response_model=Envelope[Dict[str, Any]])
def list_break_glass_grants(
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session)
):
    """List active break-glass grants."""
    current_time = now()
    if actor.role in [Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR", Role.AUDITOR.value, "AUDITOR"]:
        stmt = (
            select(BreakGlassGrant)
            .where(BreakGlassGrant.expires_at > current_time, col(BreakGlassGrant.is_revoked).is_(False))
            .order_by(BreakGlassGrant.created_at.desc())
        )
    else:
        stmt = (
            select(BreakGlassGrant)
            .where(
                BreakGlassGrant.user_id == actor.id,
                BreakGlassGrant.expires_at > current_time,
                col(BreakGlassGrant.is_revoked).is_(False)
            )
            .order_by(BreakGlassGrant.created_at.desc())
        )

    grants = session.exec(stmt).all()
    return Envelope(
        data={
            "grants": [
                {
                    "id": g.id,
                    "user_id": g.user_id,
                    "entity": g.entity,
                    "field": g.field,
                    "reason": g.reason,
                    "granted_by": g.granted_by,
                    "expires_at": g.expires_at.isoformat(),
                    "created_at": g.created_at.isoformat(),
                    "is_active": True
                }
                for g in grants
            ]
        }
    )
