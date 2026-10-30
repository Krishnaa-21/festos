# OWNER: P2
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RankedReplacement(BaseModel):
    vendor_id: str
    vendor_name: str
    spare_capacity: int
    dietary_match: str  # e.g. "EXACT (vegetarian)" | "PARTIAL"
    compliance_status: str  # VALID_THROUGHOUT | EXPIRES_DURING_FESTIVAL | EXPIRED
    operating_hours: str
    can_absorb_load: bool
    rate_per_meal_inr: float
    cost_delta_inr: float
    rank: int
    rationale: str


class BackupCapacityCheck(BaseModel):
    total_replacement_capacity: int
    required_capacity: int
    deficit: int = 0
    can_absorb_load: bool
    warning: Optional[str] = None


class VendorShutdownAnalysisRequest(BaseModel):
    from_time: Optional[datetime] = None
    reason: Optional[str] = None


class VendorShutdownExecuteRequest(BaseModel):
    from_time: Optional[datetime] = None
    reason: str
    replacement_vendor_id: Optional[str] = None
    dispatch_notifications: bool = True


class VendorShutdownAnalysisResult(BaseModel):
    vendor_id: str
    vendor_name: str
    from_time: str
    affected_locations: List[str]
    affected_meal_slots: List[str]
    lost_capacity: int
    dietary_gaps: List[Dict[str, Any]]
    ranked_replacements: List[RankedReplacement]
    replacement_candidates: List[RankedReplacement] = Field(default_factory=list)
    backup_capacity_check: BackupCapacityCheck
    cost_change_inr: float
    recommendation: str
    notification_drafts: List[Dict[str, Any]]


class VendorSummarySchema(BaseModel):
    id: str
    name: str
    status: str
    menu_description: Optional[str] = None
    dietary_options: Optional[str] = None
    declared_categories: List[str] = Field(default_factory=list)
    unverified_categories: List[str] = Field(default_factory=list)
    hours: Optional[str] = None
    capacity: Optional[int] = None
    hygiene_certificate_expiry: Optional[str] = None
    compliance_status: str
    payment_terms: Optional[str] = None
    base_rate_per_meal_inr: float = 180.0
    contact_phone: Optional[str] = None
    assigned_slots_count: int = 0


class VendorDetailSchema(BaseModel):
    id: str
    name: str
    status: str
    menu_description: Optional[str] = None
    dietary_options: Optional[str] = None
    declared_categories: List[str] = Field(default_factory=list)
    unverified_categories: List[str] = Field(default_factory=list)
    hours: Optional[str] = None
    capacity: Optional[int] = None
    hygiene_certificate_expiry: Optional[str] = None
    compliance_status: str
    payment_terms: Optional[str] = None
    base_rate_per_meal_inr: float = 180.0
    contact_phone: Optional[str] = None
    assignments: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_flags: List[Dict[str, Any]] = Field(default_factory=list)
