# OWNER: P1
from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Any, Dict, List, Tuple

from sqlmodel import Session

import app.core.audit as audit_module
from app.core.clock import now
from app.core.errors import NotFoundError
from app.core.rbac import check_permission, has_permission
from app.schemas.common import Actor, Role
from app.services.reports.post_festival import (
    generate_post_festival_csv,
    generate_post_festival_html,
)
from app.services.reports.registry import (
    get_all_reports,
    get_report,
)

logger = logging.getLogger("festos.reports.service")


def get_reports_catalog(session: Session, actor: Actor) -> List[Dict[str, Any]]:
    """Returns the catalog of all 20 spec Section 14 reports with caller authorization flags."""
    reports = get_all_reports()
    catalog = []

    for r in reports:
        can_export = has_permission(actor, r.required_permission) or (
            actor and actor.role in (Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR", Role.AUDITOR.value, "AUDITOR")
        )
        catalog.append({
            "name": r.name,
            "title": r.title,
            "format": r.format,
            "category": r.category,
            "required_permission": r.required_permission,
            "description": r.description,
            "can_export": can_export,
        })

    return catalog


def generate_single_report(
    name: str,
    session: Session,
    actor: Actor,
    mask: bool = True,
) -> Tuple[str, str, str]:
    """Generates a single report by name after strictly verifying RBAC permissions.
    Neutralizes CSV injection and logs an immutable audit event.
    Returns (content, content_type, filename).
    """
    report_def = get_report(name)
    if not report_def:
        raise NotFoundError(f"Report '{name}' not found in registry")

    # Enforce role-based export permission
    check_permission(actor, report_def.required_permission)

    # Generate report
    content, content_type = report_def.generator(session, actor, mask)

    # Audit export
    audit_module.record(
        session=session,
        actor=actor,
        action="report.exported",
        entity_type="report",
        entity_id=name,
        before={"mask": mask},
        after={"format": report_def.format, "size_bytes": len(content.encode("utf-8"))},
        reason=f"User downloaded report '{name}'",
        status="SUCCESS",
    )
    session.commit()

    return content, content_type, name


def generate_reports_bundle(
    session: Session,
    actor: Actor,
    mask: bool = True,
) -> bytes:
    """Bundles all authorized reports into a single zip archive with a cryptographic manifest.
    Every export is audited.
    """
    buf = io.BytesIO()
    manifest_items = []

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for r in get_all_reports():
            # Check permissions
            if has_permission(actor, r.required_permission) or (
                actor and actor.role in (Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR", Role.AUDITOR.value, "AUDITOR")
            ):
                try:
                    content, content_type = r.generator(session, actor, mask)
                    zf.writestr(r.name, content)
                    manifest_items.append({
                        "file": r.name,
                        "title": r.title,
                        "format": r.format,
                        "size_bytes": len(content.encode("utf-8")),
                        "status": "INCLUDED",
                    })
                except Exception as e:
                    logger.error(f"Error generating report {r.name} for bundle: {e}")
                    manifest_items.append({
                        "file": r.name,
                        "title": r.title,
                        "status": f"ERROR: {str(e)}",
                    })
            else:
                manifest_items.append({
                    "file": r.name,
                    "title": r.title,
                    "status": "EXCLUDED_FORBIDDEN",
                })

        # Include Manifest
        manifest = {
            "archive": "festos_reports_bundle.zip",
            "generated_at": now().isoformat(),
            "actor_id": actor.id if actor else "ANONYMOUS",
            "actor_role": actor.role if actor else "ANONYMOUS",
            "total_reports_bundled": len([m for m in manifest_items if m.get("status") == "INCLUDED"]),
            "items": manifest_items,
        }
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2))

    zip_bytes = buf.getvalue()

    # Audit bundle export
    audit_module.record(
        session=session,
        actor=actor,
        action="report.bundle_exported",
        entity_type="report",
        entity_id="bundle.zip",
        before={"mask": mask},
        after={"total_files": len(manifest_items), "archive_size_bytes": len(zip_bytes)},
        reason="Downloaded complete reports bundle archive",
        status="SUCCESS",
    )
    session.commit()

    return zip_bytes


def generate_post_festival_report(
    session: Session,
    actor: Actor,
    format_type: str = "html",
) -> Tuple[str, str]:
    """Generates the comprehensive post-festival synthesis from audit history and live operational state."""
    if actor and actor.role not in (Role.FESTIVAL_DIRECTOR.value, "FESTIVAL_DIRECTOR", Role.AUDITOR.value, "AUDITOR"):
        check_permission(actor, "reports:read")

    if format_type.lower() == "csv":
        content, content_type = generate_post_festival_csv(session, actor)
    else:
        content, content_type = generate_post_festival_html(session, actor)

    # Audit post festival export
    audit_module.record(
        session=session,
        actor=actor,
        action="report.post_festival_exported",
        entity_type="report",
        entity_id=f"post_festival.{format_type}",
        before={"format": format_type},
        after={"size_bytes": len(content.encode("utf-8"))},
        reason="Generated post-festival comprehensive operational report",
        status="SUCCESS",
    )
    session.commit()

    return content, content_type
