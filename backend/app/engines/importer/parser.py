# OWNER: P2
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.engines.importer.mapping import (
    ColumnMappingConfig,
    get_mapping_config,
    map_and_normalize_row,
)
from app.engines.importer.validator import (
    ValidationIssue,
    validate_participant_row,
)


@dataclass
class ParsedImportResult:
    sheet_name: str
    content_hash: str
    total_rows: int
    imported_rows: int
    quarantined_rows: int
    raw_records: List[Dict[str, Any]] = field(default_factory=list)
    staged_records: List[Dict[str, Any]] = field(default_factory=list)
    quarantine_records: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    matched_columns: Dict[str, str] = field(default_factory=dict)
    missing_columns: List[str] = field(default_factory=list)


class MalformedCSVError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MissingColumnsError(Exception):
    def __init__(self, missing_columns: List[str], sheet_name: str):
        msg = f"Missing required columns in {sheet_name}: {', '.join(missing_columns)}"
        super().__init__(msg)
        self.missing_columns = missing_columns
        self.sheet_name = sheet_name


def parse_csv_content(
    content: bytes,
    sheet_name: str,
    mapping_cfg: Optional[ColumnMappingConfig] = None,
    minor_age_threshold: int = 18,
) -> ParsedImportResult:
    """Parses raw CSV content into raw, staged, and quarantined records with full validation.
    Pure logic: no DB access, no FastAPI imports.
    """
    # 1. Compute SHA-256 content hash for idempotency
    content_hash = hashlib.sha256(content).hexdigest()

    # 2. Check for binary corruption / null bytes
    if b"\x00" in content:
        raise MalformedCSVError("Malformed CSV: binary file or null byte corruption detected")

    # 3. Decode text tolerantly
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if not text:
        raise MalformedCSVError("Unable to decode CSV file with supported encodings (UTF-8, Latin-1)")

    if "\x00" in text:
        raise MalformedCSVError("Malformed CSV: null byte corruption detected")


    # 3. Read CSV
    stream = io.StringIO(text)
    try:
        reader = csv.reader(stream)
        headers = next(reader, None)
    except Exception as e:
        raise MalformedCSVError(f"Malformed CSV: failed to parse header: {e}")

    if not headers or all(not h.strip() for h in headers):
        raise MalformedCSVError("Malformed CSV: header row is missing or empty")

    # Clean headers
    clean_headers = [h.strip() for h in headers]

    # 4. Resolve column mapping
    clean_sheet = sheet_name.replace(".csv", "").strip()
    if isinstance(mapping_cfg, str):
        clean_sheet = mapping_cfg.replace(".csv", "").strip()
        mapping_cfg = None
    cfg = mapping_cfg or get_mapping_config(clean_sheet)
    matched_cols, missing_cols = cfg.validate_headers(clean_headers)

    if missing_cols:
        raise MissingColumnsError(missing_cols, clean_sheet)


    raw_records: List[Dict[str, Any]] = []
    staged_records: List[Dict[str, Any]] = []
    quarantine_records: List[Dict[str, Any]] = []
    all_issues: List[ValidationIssue] = []

    row_index = 0
    try:
        for row in reader:
            row_index += 1
            # Build raw dict
            raw_row: Dict[str, str] = {}
            for idx, col in enumerate(clean_headers):
                val = row[idx] if idx < len(row) else ""
                raw_row[col] = val

            # Determine source row ID
            source_row_id = (
                raw_row.get("participant_id")
                or raw_row.get("id")
                or raw_row.get("contingent_id")
                or raw_row.get("event_id")
                or raw_row.get("venue_id")
                or raw_row.get("member_id")
                or raw_row.get("room_id")
                or raw_row.get("property_id")
                or raw_row.get("item_id")
                or raw_row.get("vendor_id")
                or f"row_{row_index}"
            ).strip()

            # Untouched raw row preserved byte-for-byte / value-for-value
            raw_records.append({
                "source_row_id": source_row_id,
                "source_sheet": clean_sheet,
                "raw_payload": dict(raw_row),
                "row_index": row_index,
            })

            # Normalized mapping
            normalized = map_and_normalize_row(raw_row, cfg, row_index)

            # Validation per sheet
            is_quarantined = False
            quarantine_reason = None

            if cfg.entity == "participant":
                is_quarantined, quarantine_reason, row_issues = validate_participant_row(
                    normalized, minor_age_threshold=minor_age_threshold
                )
                all_issues.extend(row_issues)

            if is_quarantined:
                quarantine_records.append({
                    "reason": f"Participant {source_row_id} has arrival scheduled at or after departure ({quarantine_reason})",
                    "reason_code": quarantine_reason or "VALIDATION_FAILED",
                    "raw_payload": dict(raw_row),
                    "source_row_id": source_row_id,
                })
            else:
                staged_records.append(normalized)


    except Exception as e:
        raise MalformedCSVError(f"Malformed CSV data at row {row_index + 1}: {e}")

    return ParsedImportResult(
        sheet_name=clean_sheet,

        content_hash=content_hash,
        total_rows=row_index,
        imported_rows=len(staged_records),
        quarantined_rows=len(quarantine_records),
        raw_records=raw_records,
        staged_records=staged_records,
        quarantine_records=quarantine_records,
        issues=all_issues,
        matched_columns=matched_cols,
        missing_columns=missing_cols,
    )
