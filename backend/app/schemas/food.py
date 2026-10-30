# OWNER: P2
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DietaryMatrixCell(BaseModel):
    meal_slot: str
    date: str
    category: str
    demand_confirmed: int
    demand_max_with_unknown: int
    valid_capacity: int
    deficit: int
    is_zero_coverage: bool
    active_vendors: List[str] = Field(default_factory=list)


class DietaryCoverageSummary(BaseModel):
    on_site_headcount: int
    valid_aggregate_capacity: int
    aggregate_shortfall: int
    zero_coverage_categories: List[str] = Field(default_factory=list)
    unknown_dietary_headcount: int


class FoodCoverageResponseData(BaseModel):
    date: str
    categories: List[str]
    meal_slots: List[str]
    summary: DietaryCoverageSummary
    matrix: List[DietaryMatrixCell]
    critical_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class MenuLabelMismatchFlag(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    flag_type: str
    menu_keyword: str
    declared_options: List[str]
    severity: str
    status: str
    message: str
    requires_human_confirmation: bool = True


class MealSlotSchema(BaseModel):
    id: str
    name: str
    date: str
    start_time: str
    end_time: str
    assigned_vendors_count: int = 0
