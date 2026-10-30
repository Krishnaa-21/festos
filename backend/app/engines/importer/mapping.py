# OWNER: P2
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from app.engines.importer.normalizers import (
    normalize_accessibility,
    normalize_condition,
    normalize_datetime,
    normalize_diet,
    normalize_gender,
    normalize_housing_preference,
    normalize_tri,
)

DEFAULT_MAPPING_DIR = Path("/home/krishna/festos/data/mapping")


class ColumnMappingConfig:
    def __init__(self, raw_config: Dict[str, Any]):
        self.file = raw_config.get("file", "")
        self.entity = raw_config.get("entity", "")
        self.target_table = raw_config.get("target_table", "")
        self.id_prefix = raw_config.get("id_prefix", "")
        self.primary_key = raw_config.get("primary_key", "id")
        self.columns_cfg = raw_config.get("columns", {})

        # Build reverse lookup: synonym (lowercase) -> canonical field info
        self._synonym_map: Dict[str, Dict[str, Any]] = {}
        self.canonical_fields: List[str] = []

        for raw_col, col_def in self.columns_cfg.items():
            canonical = col_def.get("canonical", raw_col)
            self.canonical_fields.append(canonical)
            synonyms = col_def.get("synonyms", [])
            all_names = set([raw_col.lower(), canonical.lower()] + [s.lower() for s in synonyms])
            for name in all_names:
                self._synonym_map[name] = {
                    "raw_col": raw_col,
                    "canonical": canonical,
                    "normalizer": col_def.get("normalizer"),
                    "type": col_def.get("type", "string"),
                    "required": col_def.get("required", False),
                }

    def resolve_header(self, header: str) -> Optional[Dict[str, Any]]:
        cleaned = header.strip().lower()
        return self._synonym_map.get(cleaned)

    def validate_headers(self, headers: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """Given a list of CSV headers:
        Returns:
            (raw_header -> canonical_field_name, list_of_missing_required_fields)
        """
        matched_canonical: Dict[str, str] = {}
        matched_canonicals_set = set()

        for h in headers:
            info = self.resolve_header(h)
            if info:
                canonical = info["canonical"]
                matched_canonical[h] = canonical
                matched_canonicals_set.add(canonical)

        missing_required = []
        for raw_col, col_def in self.columns_cfg.items():
            if col_def.get("required", False):
                canonical = col_def.get("canonical", raw_col)
                if canonical not in matched_canonicals_set:
                    missing_required.append(raw_col)

        return matched_canonical, missing_required


_cached_mappings: Dict[str, ColumnMappingConfig] = {}


def get_mapping_config(sheet_name: str, mapping_dir: Optional[Path] = None) -> ColumnMappingConfig:
    """Loads and caches mapping configuration for a sheet or file name."""
    clean_name = sheet_name.replace(".csv", "").strip().lower()
    if clean_name in _cached_mappings:
        return _cached_mappings[clean_name]

    directory = mapping_dir or DEFAULT_MAPPING_DIR
    candidates = [
        directory / f"{clean_name}.yaml",
        directory / f"{clean_name}.yml",
    ]

    target_file = None
    for c in candidates:
        if c.exists():
            target_file = c
            break

    if not target_file:
        # Fallback default empty config
        cfg = ColumnMappingConfig({"file": f"{clean_name}.csv", "entity": clean_name})
        _cached_mappings[clean_name] = cfg
        return cfg

    with open(target_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    cfg = ColumnMappingConfig(data)
    _cached_mappings[clean_name] = cfg
    return cfg


def map_and_normalize_row(
    raw_row: Dict[str, str],
    cfg: ColumnMappingConfig,
    row_index: int = 1,
) -> Dict[str, Any]:
    """Maps a single raw row dictionary to canonical fields with tolerant type normalization."""
    result: Dict[str, Any] = {}

    for raw_header, raw_val in raw_row.items():
        info = cfg.resolve_header(raw_header)
        if not info:
            continue

        canonical = info["canonical"]
        col_type = info.get("type", "string")
        norm = info.get("normalizer")

        # Strip value
        val_str = str(raw_val).strip() if raw_val is not None else ""

        # Normalize based on rule
        if norm == "gender":
            result[canonical] = normalize_gender(val_str)
        elif norm == "diet":
            result[canonical] = normalize_diet(val_str)
        elif norm == "tri":
            result[canonical] = normalize_tri(val_str)
        elif norm == "accessibility":
            result[canonical] = normalize_accessibility(val_str)
        elif norm == "housing_preference":
            result[canonical] = normalize_housing_preference(val_str)
        elif norm == "condition":
            result[canonical] = normalize_condition(val_str)
        elif col_type == "integer":
            try:
                result[canonical] = int(val_str) if val_str else None
            except ValueError:
                result[canonical] = None
        elif col_type == "float":
            try:
                result[canonical] = float(val_str) if val_str else None
            except ValueError:
                result[canonical] = None
        elif col_type == "datetime":
            result[canonical] = normalize_datetime(val_str)
        elif col_type == "date":
            # Keep as YYYY-MM-DD string or parse
            result[canonical] = val_str if val_str else None
        else:
            result[canonical] = val_str if val_str != "" else None

    # Handle Stable ID Generation per Context section 4
    # Keep source IDs (C05, VND05, P0001, EXT01...) where present
    source_id = (
        raw_row.get("participant_id")
        or raw_row.get("contingent_id")
        or raw_row.get("event_id")
        or raw_row.get("venue_id")
        or raw_row.get("member_id")
        or raw_row.get("room_id")
        or raw_row.get("property_id")
        or raw_row.get("item_id")
        or raw_row.get("vendor_id")
    )

    if source_id:
        result["id"] = source_id.strip()
        result["source_row_id"] = source_id.strip()
    elif "id" not in result or not result["id"]:
        prefix = cfg.id_prefix or f"{cfg.entity[:3]}_"
        result["id"] = f"{prefix}{row_index:04d}"

    return result
