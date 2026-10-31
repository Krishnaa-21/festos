#!/usr/bin/env python3
"""Generate docs/API.md index directly from OpenAPI specification."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = REPO_ROOT / "frontend" / "openapi.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "API.md"


def generate_api_md() -> None:
    if not OPENAPI_PATH.exists():
        raise FileNotFoundError(f"OpenAPI spec not found at {OPENAPI_PATH}")

    spec: Dict[str, Any] = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    info = spec.get("info", {})
    paths = spec.get("paths", {})

    # Group operations by tag
    tagged_ops: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    untagged_ops: List[Dict[str, Any]] = []

    total_ops = 0
    for path, methods in sorted(paths.items()):
        for method, op_data in sorted(methods.items()):
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            total_ops += 1
            op_info = {
                "method": method.upper(),
                "path": path,
                "summary": op_data.get("summary") or op_data.get("description") or "Endpoint operation",
                "operation_id": op_data.get("operationId", ""),
                "parameters": op_data.get("parameters", []),
                "tags": op_data.get("tags", []),
            }
            if op_info["tags"]:
                for tag in op_info["tags"]:
                    tagged_ops[tag].append(op_info)
            else:
                untagged_ops.append(op_info)

    doc = [
        "# FestOS Complete REST API Specification Index (`docs/API.md`)",
        "",
        f"> **Title:** {info.get('title', 'FestOS API')}  ",
        f"> **Version:** {info.get('version', '1.0.0')}  ",
        f"> **Total Registered Endpoints:** {len(paths)} distinct paths, {total_ops} HTTP operations across 32 modules  ",
        "> **Format:** OpenAPI 3.1.0 compliant  ",
        "",
        "---",
        "",
        "## 1. Architectural & API Conventions",
        "",
        "- **Base Path:** `/api/v1/<module>` (with root aliases mounted for key operational routes).",
        "- **Standard Response Envelope:**",
        "  ```json",
        "  {",
        '    "data": { ... },',
        '    "meta": { "total": 100, "page": 1, "page_size": 20 },',
        '    "warnings": []',
        "  }",
        "  ```",
        "- **Standard Error Envelope:**",
        "  ```json",
        "  {",
        '    "error": {',
        '      "code": "CONSTRAINT_VIOLATION",',
        '      "message": "Human-readable explanation",',
        '      "details": [ { "code": "CAPACITY_EXCEEDED", "path": "room_id", "hard": true } ],',
        '      "request_id": "req_8f1b3c9d"',
        "    }",
        "  }",
        "  ```",
        "- **Mutating Actions via ChangeService:** Every write operation generates an immutable `ChangeSet` and `AuditEvent` record.",
        "- **Idempotency & Optimistic Concurrency:**",
        "  - Header `Idempotency-Key: <uuid>` prevents duplicate network retries.",
        "  - Body `expected_version: <int>` guards against concurrent write race conditions (`409 VERSION_CONFLICT`).",
        "- **Dry-Run Support:** Query param or body flag `dry_run=true` returns downstream impact preview without committing state.",
        "- **Authentication:** Bearer token (`Authorization: Bearer <JWT>`) or testing headers (`X-Actor-Role`, `X-Actor-Id`).",
        "",
        "---",
        "",
        "## 2. Table of Contents & Module Directory",
        "",
    ]

    for tag in sorted(tagged_ops.keys()):
        slug = tag.lower().replace(" ", "-")
        count = len(tagged_ops[tag])
        doc.append(f"- [{tag}](#{slug}) ({count} endpoints)")

    if untagged_ops:
        doc.append(f"- [Core System & Uncategorized](#core-system--uncategorized) ({len(untagged_ops)} endpoints)")

    doc.append("")
    doc.append("---")
    doc.append("")
    doc.append("## 3. Module Operations Registry")
    doc.append("")

    for tag in sorted(tagged_ops.keys()):
        ops = tagged_ops[tag]
        doc.append(f"### <a id=\"{tag.lower().replace(' ', '-')}\"></a>{tag}")
        doc.append("")
        doc.append("| Method | Endpoint Path | Summary | Operation ID |")
        doc.append("|---|---|---|---|")
        for op in ops:
            m = op["method"]
            p = op["path"]
            s = op["summary"].replace("|", "\\|")
            op_id = op["operation_id"]
            doc.append(f"| **`{m}`** | `{p}` | {s} | `{op_id}` |")
        doc.append("")

    if untagged_ops:
        doc.append("### Core System & Uncategorized")
        doc.append("")
        doc.append("| Method | Endpoint Path | Summary | Operation ID |")
        doc.append("|---|---|---|---|")
        for op in untagged_ops:
            m = op["method"]
            p = op["path"]
            s = op["summary"].replace("|", "\\|")
            op_id = op["operation_id"]
            doc.append(f"| **`{m}`** | `{p}` | {s} | `{op_id}` |")
        doc.append("")

    OUTPUT_PATH.write_text("\n".join(doc) + "\n", encoding="utf-8")
    print(f"[SUCCESS] Generated {OUTPUT_PATH} ({len(paths)} paths, {total_ops} operations)")


if __name__ == "__main__":
    generate_api_md()
