# OWNER: P2
from __future__ import annotations

import csv
import io
from typing import List

from app.core.clock import now
from app.engines.accommodation.types import (
    DemandTimelineResult,
    PlanResult,
    UnplacedSnapshot,
)
from app.schemas.common import AlternativeRejected, DecisionCard, SoftRelaxed


def generate_plan_csv(plan: PlanResult) -> str:
    """Generate CSV string of stay assignments for a plan."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "participant_id",
        "resource_id",
        "bed_key",
        "is_external",
        "start_at",
        "end_at",
        "cost_inr",
        "constraints_satisfied",
        "soft_constraints_relaxed",
    ])
    for a in plan.assignments:
        sat_str = "; ".join(a.explanation.constraints_satisfied)
        rel_str = "; ".join(f"{r.get('constraint')}: {r.get('reason')}" for r in a.explanation.soft_constraints_relaxed)
        writer.writerow([
            a.participant_id,
            a.resource_id,
            a.bed_key,
            "true" if a.is_external else "false",
            a.start_at.isoformat(),
            a.end_at.isoformat(),
            f"{a.cost_inr:.2f}",
            sat_str,
            rel_str,
        ])
    return output.getvalue()


def generate_shortage_report_csv(unplaced: List[UnplacedSnapshot]) -> str:
    """Generate CSV string of unplaced participants with blocking reasons and counterfactuals."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "participant_id",
        "name",
        "contingent_id",
        "college",
        "blocking_reason",
        "accessibility_needed",
        "housing_preference",
        "gender",
        "missing_information",
        "counterfactual_impact",
    ])
    for u in unplaced:
        writer.writerow([
            u.participant_id,
            u.name,
            u.contingent_id,
            u.college,
            u.blocking_reason,
            "true" if u.accessibility_needed else "false",
            u.housing_preference,
            u.gender,
            u.missing_information,
            u.counterfactual_impact,
        ])
    return output.getvalue()


def generate_accommodation_summary_csv(plans: List[PlanResult]) -> str:
    """Generate summary CSV comparing all candidate plans."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "plan_id",
        "kind",
        "name",
        "on_campus_placed",
        "external_placed",
        "unplaced_count",
        "contingent_splits",
        "total_cost_inr",
        "safety_flags_count",
        "accessibility_issues_count",
        "relaxed_constraints_count",
        "minors_external_count",
        "plan_hash",
        "sacrifices_summary",
    ])
    for p in plans:
        m = p.metrics
        writer.writerow([
            p.plan_id,
            p.kind,
            p.name,
            m.on_campus_placed,
            m.external_placed,
            m.unplaced_count,
            m.contingent_splits,
            f"{m.total_cost_inr:.2f}",
            m.safety_flags_count,
            m.accessibility_issues_count,
            m.relaxed_constraints_count,
            m.minors_external_count,
            p.plan_hash,
            p.sacrifices_summary,
        ])
    return output.getvalue()


def generate_bed_demand_timeline_csv(timeline_result: DemandTimelineResult) -> str:
    """Generate CSV of bed demand timeline points."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "confirmed_demand",
        "possible_demand",
        "cleaning_beds",
        "available_supply",
    ])
    for pt in timeline_result.timeline:
        writer.writerow([
            pt.timestamp.isoformat(),
            pt.confirmed_demand,
            pt.possible_demand,
            pt.cleaning_beds,
            pt.available_supply,
        ])
    return output.getvalue()


def generate_decision_card(plan: PlanResult) -> DecisionCard:
    """Create a structured DecisionCard for a generated plan."""
    m = plan.metrics
    soft_relaxed: List[SoftRelaxed] = []
    if m.contingent_splits > 0:
        soft_relaxed.append(
            SoftRelaxed(
                constraint="CONTINGENT_COHESION",
                reason=f"Split across {m.contingent_splits} locations due to hostel and property bed capacity limits.",
            )
        )
    if m.total_cost_inr > 0:
        soft_relaxed.append(
            SoftRelaxed(
                constraint="BUDGET_EXPENDITURE",
                reason=f"Committed ₹{m.total_cost_inr:,.0f} external stay expenditure to place overflow participants.",
            )
        )

    alternatives: List[AlternativeRejected] = []
    if plan.kind == "A":
        alternatives.append(
            AlternativeRejected(
                option="Plan B (Cost-First)",
                why="Higher contingent fragmentation and travel disruption.",
            )
        )
    elif plan.kind == "B":
        alternatives.append(
            AlternativeRejected(
                option="Plan A (Cohesion-First)",
                why="Higher external property unit rates.",
            )
        )
    else:
        alternatives.append(
            AlternativeRejected(
                option="Extreme single-objective plans (A or B)",
                why="Plan C achieves balanced multi-objective trade-off without extreme cohesion or cost compromises.",
            )
        )

    return DecisionCard(
        id=f"dec_{plan.plan_id}",
        subject=f"Accommodation Allocation: {plan.name}",
        recommendation=plan.sacrifices_summary,
        hard_satisfied=(m.accessibility_issues_count == 0),
        soft_relaxed=soft_relaxed,
        alternatives_rejected=alternatives,
        cost_impact=m.total_cost_inr,
        people_affected=m.on_campus_placed + m.external_placed,
        approved_by=None,
        created_at=now(),
    )
