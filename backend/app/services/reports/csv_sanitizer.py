# OWNER: P1
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_value(val: Any) -> Any:
    """Neutralizes CSV injection formula execution in Excel/Calc/Spreadsheets.
    Prefixes any string cell starting with =, +, -, @, \t, \r with a single quote (').
    """
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    s = str(val)
    if s.startswith(INJECTION_PREFIXES):
        return f"'{s}"
    return s


def sanitize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizes each cell in a dictionary row."""
    return {k: sanitize_csv_value(v) for k, v in row.items()}


def write_sanitized_csv(rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> str:
    """Generates a CSV string with all formula cells neutralized against CSV injection."""
    if not rows:
        if fieldnames:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fieldnames)
            writer.writeheader()
            return buf.getvalue()
        return ""

    if not fieldnames:
        fieldnames = list(rows[0].keys())

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for r in rows:
        sanitized = sanitize_row(r)
        writer.writerow(sanitized)

    return buf.getvalue()
