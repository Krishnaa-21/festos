# OWNER: P3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token. Minimal stub for foundation."""
    try:
        from jose import jwt
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MIN))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    except Exception:
        return "dev-mock-jwt-token"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT access token."""
    try:
        from jose import jwt
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None
