# OWNER: P1
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from sqlmodel import Session

from app.schemas.common import Actor
from app.services.reports.generators import (
    gen_accommodation_plan_a,
    gen_accommodation_plan_b,
    gen_accommodation_plan_c,
    gen_accommodation_summary,
    gen_assumptions_md,
    gen_audit_report,
    gen_bed_demand_timeline,
    gen_conflicts_report,
    gen_data_quality_report,
    gen_equipment_gap,
    gen_incident_report,
    gen_inventory_plan,
    gen_reconciliation_report,
    gen_resource_load_timeline,
    gen_schedule_plan,
    gen_shortage_report,
    gen_staff_coverage,
    gen_unscheduled_entrants,
    gen_vendor_compliance,
    gen_vendor_coverage,
)


@dataclass
class ReportDefinition:
    name: str
    title: str
    format: str
    category: str
    required_permission: str
    description: str
    generator: Callable[[Session, Actor, bool], Tuple[str, str]]


REPORT_REGISTRY: Dict[str, ReportDefinition] = {
    "reconciliation_report.csv": ReportDefinition(
        name="reconciliation_report.csv",
        title="Participant Reconciliation Report",
        format="csv",
        category="participants",
        required_permission="reconciliation:export",
        description="Explains participant count variance, raw vs narrative gap, duplicates, and quarantined records",
        generator=gen_reconciliation_report,
    ),
    "data_quality_report.csv": ReportDefinition(
        name="data_quality_report.csv",
        title="Data Quality & Field Verification Report",
        format="csv",
        category="imports",
        required_permission="imports:export",
        description="Audit of missing fields, invalid formats, and pending UNKNOWN verifications",
        generator=gen_data_quality_report,
    ),
    "accommodation_plan_A.csv": ReportDefinition(
        name="accommodation_plan_A.csv",
        title="Accommodation Plan A (Cohesion First)",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Cohesion-prioritized room and bed allocation keeping college contingents intact",
        generator=gen_accommodation_plan_a,
    ),
    "accommodation_plan_B.csv": ReportDefinition(
        name="accommodation_plan_B.csv",
        title="Accommodation Plan B (Cost First)",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Cost-minimizing accommodation plan maximizing on-campus bed utilization before external stays",
        generator=gen_accommodation_plan_b,
    ),
    "accommodation_plan_C.csv": ReportDefinition(
        name="accommodation_plan_C.csv",
        title="Accommodation Plan C (Balanced)",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Balanced compromise optimization across cohesion, lodging cost, and venue proximity",
        generator=gen_accommodation_plan_c,
    ),
    "shortage_report.csv": ReportDefinition(
        name="shortage_report.csv",
        title="Housing Shortage & Unplaced Report",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Documented list of unplaced participants, capacity bottlenecks, and external bed requirements",
        generator=gen_shortage_report,
    ),
    "accommodation_summary.csv": ReportDefinition(
        name="accommodation_summary.csv",
        title="Contingent Accommodation Distribution Summary",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Contingent-level breakdown of campus versus external bed placement and lodging expenditure",
        generator=gen_accommodation_summary,
    ),
    "schedule_plan.csv": ReportDefinition(
        name="schedule_plan.csv",
        title="Event Schedule Master Plan",
        format="csv",
        category="schedule",
        required_permission="schedule:export",
        description="Generated festival schedule across all 31 events, sessions, heats, and assigned venues",
        generator=gen_schedule_plan,
    ),
    "conflicts_report.csv": ReportDefinition(
        name="conflicts_report.csv",
        title="Operational Conflicts & Resource Overlaps Report",
        format="csv",
        category="schedule",
        required_permission="schedule:export",
        description="Detected participant overlaps, venue double-bookings, travel violations, and staff shortages",
        generator=gen_conflicts_report,
    ),
    "unscheduled_entrants.csv": ReportDefinition(
        name="unscheduled_entrants.csv",
        title="Unscheduled Entrants Report",
        format="csv",
        category="schedule",
        required_permission="schedule:export",
        description="Registered participants without scheduled session slots due to heat capacity limits",
        generator=gen_unscheduled_entrants,
    ),
    "inventory_plan.csv": ReportDefinition(
        name="inventory_plan.csv",
        title="Logistics & Merchandise Inventory Plan",
        format="csv",
        category="logistics",
        required_permission="logistics:export",
        description="Stock projection: on-hand, reserved, in-transit, damaged, and available items",
        generator=gen_inventory_plan,
    ),
    "equipment_gap.csv": ReportDefinition(
        name="equipment_gap.csv",
        title="Equipment Availability & Peak Gap Analysis",
        format="csv",
        category="logistics",
        required_permission="logistics:export",
        description="Critical equipment items with shortfalls against simultaneous event requirements",
        generator=gen_equipment_gap,
    ),
    "vendor_coverage.csv": ReportDefinition(
        name="vendor_coverage.csv",
        title="Food Vendor Dietary Coverage Report",
        format="csv",
        category="food",
        required_permission="food:export",
        description="Meal slot coverage analysis for Regular, Jain, Vegetarian, and Vegan diets",
        generator=gen_vendor_coverage,
    ),
    "vendor_compliance.csv": ReportDefinition(
        name="vendor_compliance.csv",
        title="Food Vendor Compliance & Licensing Register",
        format="csv",
        category="vendors",
        required_permission="vendors:export",
        description="Status of food vendor FSSAI licenses, hygiene certificates, and health audit ratings",
        generator=gen_vendor_compliance,
    ),
    "staff_coverage.csv": ReportDefinition(
        name="staff_coverage.csv",
        title="Volunteer & Core Team Coverage Gap Report",
        format="csv",
        category="staff",
        required_permission="staff:export",
        description="Comparison of volunteer shift requirements versus staff presence across venues",
        generator=gen_staff_coverage,
    ),
    "bed_demand_timeline.csv": ReportDefinition(
        name="bed_demand_timeline.csv",
        title="Accommodation Demand Timeline",
        format="csv",
        category="accommodation",
        required_permission="accommodation:export",
        description="Day-by-day bed demand, campus occupancy, and external property spillover",
        generator=gen_bed_demand_timeline,
    ),
    "resource_load_timeline.csv": ReportDefinition(
        name="resource_load_timeline.csv",
        title="Operational Resource Load Timeline",
        format="csv",
        category="logistics",
        required_permission="logistics:export",
        description="Hourly staffing and equipment utilization timeline across active event sessions",
        generator=gen_resource_load_timeline,
    ),
    "assumptions.md": ReportDefinition(
        name="assumptions.md",
        title="Operational Assumptions Master Register",
        format="md",
        category="assumptions",
        required_permission="assumptions:export",
        description="Authoritative documentation of all system assumptions, buffer parameters, weights, and owners",
        generator=gen_assumptions_md,
    ),
    "incident_report.csv": ReportDefinition(
        name="incident_report.csv",
        title="Operational Incident & Disruption Log",
        format="csv",
        category="incidents",
        required_permission="incidents:export",
        description="Comprehensive log of operational incidents, severity levels, and resolution actions",
        generator=gen_incident_report,
    ),
    "audit_report.csv": ReportDefinition(
        name="audit_report.csv",
        title="Cryptographic Decision & Mutation Audit Trail",
        format="csv",
        category="audit",
        required_permission="audit:export",
        description="Append-only cryptographic audit trail recording all system state mutations and exports",
        generator=gen_audit_report,
    ),
}


def get_all_reports() -> List[ReportDefinition]:
    """Returns the list of all 20 registered reports."""
    return list(REPORT_REGISTRY.values())


def get_report(name: str) -> Optional[ReportDefinition]:
    """Retrieves a report definition by its canonical file name."""
    return REPORT_REGISTRY.get(name)
