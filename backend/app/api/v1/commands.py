# OWNER: P1
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_actor
from app.core.errors import RateLimitedError
from app.schemas.common import Actor, Envelope
from app.services.commands.schemas import (
    ExecuteRequest,
    ExecuteResponseData,
    ParseRequest,
    ParseResponseData,
)
from app.services.commands.service import execute_command, parse_command
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session

router = APIRouter(prefix="/commands", tags=["Commands"])

# In-memory sliding window rate limiter for commands (60 requests/minute per client)
_COMMAND_RATE_LIMITS: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 60


def check_command_rate_limit(client_id: str) -> None:
    current_time = time.time()
    timestamps = _COMMAND_RATE_LIMITS[client_id]
    valid_timestamps = [t for t in timestamps if current_time - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(valid_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise RateLimitedError("Commands endpoint rate limit exceeded (60 requests per minute). Please try again later.")
    valid_timestamps.append(current_time)
    _COMMAND_RATE_LIMITS[client_id] = valid_timestamps


@router.post("/parse", response_model=Envelope[ParseResponseData], status_code=status.HTTP_200_OK)
def parse_natural_command(
    req: ParseRequest,
    request: Request,
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Envelope[ParseResponseData]:
    """Parses natural-language text into a strict structured command schema with operator explanation."""
    if not settings.ENABLE_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The natural-language command bar module is disabled by feature flag (ENABLE_COMMANDS=false)",
        )
    client_id = actor.id if actor else (request.client.host if request.client else "unknown_client")
    check_command_rate_limit(client_id)

    command, explanation, confidence, parser_mode = parse_command(
        text=req.text,
        context=req.context,
        actor=actor,
        session=session,
    )

    data = ParseResponseData(
        command=command,
        explanation=explanation,
        confidence=confidence,
        parser_mode=parser_mode,
    )

    return Envelope(
        data=data,
        meta={"parser_mode": parser_mode, "confidence": confidence},
        warnings=[],
    )


@router.post("/execute", response_model=Envelope[ExecuteResponseData], status_code=status.HTTP_200_OK)
def execute_structured_command(
    req: ExecuteRequest,
    request: Request,
    response: Response,
    actor: Actor = Depends(get_actor),
    session: Session = Depends(get_session),
) -> Envelope[ExecuteResponseData]:
    """Executes a structured command deterministically.
    - Read-only commands execute and return results immediately (HTTP 200).
    - Mutating commands create a dry-run proposal requiring approval (HTTP 202).
    """
    if not settings.ENABLE_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The natural-language command bar module is disabled by feature flag (ENABLE_COMMANDS=false)",
        )
    client_id = actor.id if actor else (request.client.host if request.client else "unknown_client")
    check_command_rate_limit(client_id)

    res = execute_command(
        command=req.command,
        actor=actor,
        session=session,
        reason=req.reason,
    )

    if res.status == "PROPOSAL_CREATED":
        response.status_code = status.HTTP_202_ACCEPTED

    return Envelope(
        data=res,
        meta={"intent": res.intent.value, "status": res.status},
        warnings=res.warnings,
    )


@router.get("", response_model=Envelope[Dict[str, Any]])
def list_command_intents(
    actor: Actor = Depends(get_actor),
):
    """Lists supported natural-language command intents and their schema definitions."""
    if not settings.ENABLE_COMMANDS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The natural-language command bar module is disabled by feature flag (ENABLE_COMMANDS=false)",
        )

    from app.services.commands.schemas import CommandIntent
    intents = [
        {"intent": i.value, "name": i.name}
        for i in CommandIntent
    ]
    return Envelope(
        data={
            "supported_intents": intents,
            "total": len(intents),
        }
    )
