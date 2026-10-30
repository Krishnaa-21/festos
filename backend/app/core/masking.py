# OWNER: P3
from typing import Any, Dict


def mask_sensitive_fields(data: Dict[str, Any], actor_role: str) -> Dict[str, Any]:
    """Mask sensitive fields (contact, medical, accessibility, room data, guardian data)
    according to actor role. Stub owned by P3.
    """
    if actor_role == "FESTIVAL_DIRECTOR":
        return data

    # Default stub behavior: leave intact or mask if role is volunteer/restricted
    return data
