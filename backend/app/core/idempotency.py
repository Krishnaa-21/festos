# OWNER: P1
import hashlib
from typing import Any, Dict, Optional

from sqlmodel import Session, select

from app.core.clock import now


def hash_request(method: str, path: str, body: bytes) -> str:
    h = hashlib.sha256()
    h.update(method.encode("utf-8"))
    h.update(path.encode("utf-8"))
    h.update(body)
    return h.hexdigest()

def check_idempotency(
    session: Session,
    key: str,
    request_hash: str
) -> Optional[Dict[str, Any]]:
    """Check if an idempotency key was previously processed.
    Returns cached response dict if found, else None.
    """
    from app.models.change import IdempotencyKey
    record = session.exec(select(IdempotencyKey).where(IdempotencyKey.key == key)).first()
    if record and record.response_body:
        return {
            "status_code": record.response_code or 200,
            "body": record.response_body
        }
    return None

def store_idempotency(
    session: Session,
    key: str,
    request_hash: str,
    response_code: int,
    response_body: Any
) -> None:
    """Store the completed request and its response under the idempotency key."""
    from app.models.change import IdempotencyKey
    record = session.exec(select(IdempotencyKey).where(IdempotencyKey.key == key)).first()
    if not record:
        record = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            response_code=response_code,
            response_body=response_body if isinstance(response_body, dict) else {"data": response_body},
            created_at=now()
        )
        session.add(record)
    else:
        record.response_code = response_code
        record.response_body = response_body if isinstance(response_body, dict) else {"data": response_body}
        session.add(record)
    session.commit()
