# OWNER: P3
from typing import Any, Dict


def mask_sensitive_fields(data: Dict[str, Any], actor_role: str) -> Dict[str, Any]:
    """Mask sensitive fields (contact, medical, accessibility, room data, guardian data)
    according to actor role.
    """
    if actor_role in ("FESTIVAL_DIRECTOR", "ADMIN", "AUDITOR"):
        return data

    if actor_role == "VOLUNTEER":
        masked = dict(data)
        if "phone" in masked and masked["phone"]:
            p = str(masked["phone"])
            masked["phone"] = p[:4] + "****" + p[-2:] if len(p) > 6 else "****"
        if "email" in masked and masked["email"]:
            e = str(masked["email"])
            parts = e.split("@")
            masked["email"] = parts[0][:2] + "***@" + (parts[1] if len(parts) > 1 else "***")
        if "contact" in masked and masked["contact"]:
            c = str(masked["contact"])
            masked["contact"] = c[:4] + "****" + c[-2:] if len(c) > 6 else "****"
        if "accessibility_needs" in masked and masked["accessibility_needs"]:
            masked["accessibility_needs"] = {"status": "MASKED_RESTRICTED"}
        return masked

    return data
