import React, { useState } from "react";
import {
  AlertTriangle,
  History,
  Edit2,
  HelpCircle,
  Sparkles,
  Search,
  Filter,
  DollarSign,
  Clock,
  Bus,
} from "lucide-react";
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  DataTable,
  Column,
  Badge,
  ConfirmWithReason,
  useToast,
  Drawer,
} from "../../components/ui";

export interface AssumptionRecord {
  id: string;
  name: string;
  category: "Accommodation" | "Transport" | "Schedule" | "Finance" | "General";
  current_value: string;
  unit?: string;
  source: string;
  owner: string;
  last_updated: string;
  updated_by: string;
  reason: string;
  impact_if_changed: string;
  is_placeholder: boolean;
  isOpenDecision?: boolean;
}

export interface AssumptionHistoryEntry {
  id: string;
  assumption_name: string;
  previous_value: string;
  new_value: string;
  updated_at: string;
  updated_by: string;
  reason: string;
}

const SEEDED_ASSUMPTIONS: AssumptionRecord[] = [
  {
    id: "asmp-1",
    name: "external_budget_inr",
    category: "Finance",
    current_value: "NULL",
    source: "FestOS Seed / Director Office",
    owner: "Festival Director",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Budget not supplied in data pack; engine runs in budget-unset mode and flags it.",
    impact_if_changed: "Sets ceiling for external property allocations (740 beds across 6 properties). Unlocks Plan B and C cost trade-offs.",
    is_placeholder: true,
    isOpenDecision: true,
  },
  {
    id: "asmp-2",
    name: "late_arrival_policy",
    category: "General",
    current_value: "PENDING_DIRECTOR_DECISION",
    source: "FestOS Operational Rulebook",
    owner: "Festival Director",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Awaiting final Director ruling on whether contingents arriving after 22:00 receive automatic buffer rooms or wildcards.",
    impact_if_changed: "Determines whether late-arriving contingents can register on Day 2 without individual bypass approvals.",
    is_placeholder: true,
    isOpenDecision: true,
  },
  {
    id: "asmp-3",
    name: "shuttle_capacity_seats",
    category: "Transport",
    current_value: "12",
    unit: "seats / vehicle",
    source: "FestOS Seed",
    owner: "Logistics Manager",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Placeholder from initial transit concept; contract with Indore bus operators pending.",
    impact_if_changed: "Changes throughput of transit waves between campus and 6 off-campus hotel properties.",
    is_placeholder: true,
    isOpenDecision: true,
  },
  {
    id: "asmp-4",
    name: "shuttle_vehicle_count",
    category: "Transport",
    current_value: "3",
    unit: "vehicles",
    source: "FestOS Seed",
    owner: "Logistics Manager",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Placeholder estimate. Vendor negotiation active.",
    impact_if_changed: "Reduces peak transit wait time from 45m to 15m if increased to 6.",
    is_placeholder: true,
    isOpenDecision: true,
  },
  {
    id: "asmp-5",
    name: "cleaning_buffer_minutes",
    category: "Accommodation",
    current_value: "180",
    unit: "minutes",
    source: "FESTOS_CONTEXT Section 10",
    owner: "Accommodation Lead",
    last_updated: "2026-10-30 09:15",
    updated_by: "Accommodation Lead",
    reason: "Prototype value; earlier concept said 60 min. Exactly one configurable cleaning buffer retained.",
    impact_if_changed: "Directly shifts room turnover windows between contingent checkout and incoming check-in.",
    is_placeholder: false,
  },
  {
    id: "asmp-6",
    name: "late_night_start",
    category: "General",
    current_value: "22:00",
    source: "IIM Indore Campus Safety Manual",
    owner: "Festival Director",
    last_updated: "2026-10-29 14:00",
    updated_by: "System Initializer",
    reason: "Campus gates close at 22:00 for security and sound curfew.",
    impact_if_changed: "Triggers Late Arrival alerts and forces security escort flag for minors.",
    is_placeholder: false,
  },
  {
    id: "asmp-7",
    name: "late_night_end",
    category: "General",
    current_value: "06:00",
    source: "IIM Indore Campus Safety Manual",
    owner: "Festival Director",
    last_updated: "2026-10-29 14:00",
    updated_by: "System Initializer",
    reason: "Morning entry gate unlock time.",
    impact_if_changed: "Sets earliest permissible scheduled rehearsal or breakfast arrival window.",
    is_placeholder: false,
  },
  {
    id: "asmp-8",
    name: "minor_age_threshold",
    category: "General",
    current_value: "18",
    unit: "years",
    source: "Legal & Safety Policy",
    owner: "Festival Director",
    last_updated: "2026-10-28 10:00",
    updated_by: "System Initializer",
    reason: "Statutory age of majority in India. Minors require faculty escort.",
    impact_if_changed: "Non-negotiable legal constraint. Flags 142 detected minors for mandatory escort verification.",
    is_placeholder: false,
  },
  {
    id: "asmp-9",
    name: "setup_buffer_min",
    category: "Schedule",
    current_value: "15",
    unit: "minutes",
    source: "Event Ops Guideline",
    owner: "Event Lead",
    last_updated: "2026-10-29 11:30",
    updated_by: "Event Lead",
    reason: "Stage preparation and audio line-check duration between events.",
    impact_if_changed: "Expanding creates schedule overruns; reducing risks stage crew collisions.",
    is_placeholder: false,
  },
  {
    id: "asmp-10",
    name: "teardown_buffer_min",
    category: "Schedule",
    current_value: "15",
    unit: "minutes",
    source: "Event Ops Guideline",
    owner: "Event Lead",
    last_updated: "2026-10-29 11:30",
    updated_by: "Event Lead",
    reason: "Post-event stage clearing and equipment inventory return.",
    impact_if_changed: "Overlaps with subsequent event staging if set below 10 min.",
    is_placeholder: false,
  },
  {
    id: "asmp-11",
    name: "venue_travel_min",
    category: "Schedule",
    current_value: "15",
    unit: "minutes",
    source: "Campus Distance Survey",
    owner: "Logistics Manager",
    last_updated: "2026-10-29 16:45",
    updated_by: "Logistics Manager",
    reason: "Average walking time between academic block and sports complex across campus.",
    impact_if_changed: "Participant schedule conflict detector flags overlapping multi-event registrations.",
    is_placeholder: false,
  },
  {
    id: "asmp-12",
    name: "round_result_buffer_min",
    category: "Schedule",
    current_value: "60",
    unit: "minutes",
    source: "Jury Protocol 2026",
    owner: "Event Lead",
    last_updated: "2026-10-29 12:00",
    updated_by: "Event Lead",
    reason: "Judges require 60 minutes for score compilation and audit verification before finalist announcement.",
    impact_if_changed: "Premature finals scheduling causes empty stage slots while scoring is tabulated.",
    is_placeholder: false,
  },
  {
    id: "asmp-13",
    name: "semifinal_ratio",
    category: "Schedule",
    current_value: "0.50",
    source: "Aarohan Tournament Bylaws",
    owner: "Event Lead",
    last_updated: "2026-10-28 09:00",
    updated_by: "Event Lead",
    reason: "Top 50% of registered contingent teams advance to semi-finals.",
    impact_if_changed: "Alters bracket sizing, judge hours, and stage bookings.",
    is_placeholder: false,
  },
  {
    id: "asmp-14",
    name: "finalist_ratio",
    category: "Schedule",
    current_value: "0.10",
    source: "Aarohan Tournament Bylaws",
    owner: "Event Lead",
    last_updated: "2026-10-28 09:00",
    updated_by: "Event Lead",
    reason: "Top 10% of field advance to Grand Finals.",
    impact_if_changed: "Sets trophy count, judge panel requirements, and auditorium slot duration.",
    is_placeholder: false,
  },
  {
    id: "asmp-15",
    name: "finalist_min",
    category: "Schedule",
    current_value: "8",
    unit: "teams / soloists",
    source: "Aarohan Tournament Bylaws",
    owner: "Event Lead",
    last_updated: "2026-10-28 09:00",
    updated_by: "Event Lead",
    reason: "Floor minimum so small-draw competitions still retain a competitive final round.",
    impact_if_changed: "Affects niche events with fewer than 15 total registrations.",
    is_placeholder: false,
  },
  {
    id: "asmp-16",
    name: "checkin_buffer_min",
    category: "General",
    current_value: "60",
    unit: "minutes",
    source: "Registration Desk Operations",
    owner: "Logistics Manager",
    last_updated: "2026-10-29 18:00",
    updated_by: "Logistics Manager",
    reason: "Expected verification, wristband application, and kit issue time per contingent.",
    impact_if_changed: "Shifts contingent arrival-to-competition readiness timeline.",
    is_placeholder: false,
  },
  {
    id: "asmp-17",
    name: "expected_participants_narrative",
    category: "General",
    current_value: "2400",
    unit: "people",
    source: "Executive Planning Committee",
    owner: "Festival Director",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Historical target narrative. Never forced over raw data; displayed side-by-side with raw 2,836 count.",
    impact_if_changed: "Baseline for executive delta reports and sponsorship claims.",
    is_placeholder: false,
  },
  {
    id: "asmp-18",
    name: "external_property_accessibility",
    category: "Accommodation",
    current_value: "UNVERIFIED",
    source: "Vendor RFPs",
    owner: "Accommodation Lead",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Audit pending physical inspection of 6 external hotels for ramp and elevator access.",
    impact_if_changed: "Wheelchair-accessible participants cannot be safely routed to external hotels until verified.",
    is_placeholder: true,
  },
  {
    id: "asmp-19",
    name: "external_property_gender_suitability",
    category: "Accommodation",
    current_value: "UNVERIFIED",
    source: "Vendor RFPs",
    owner: "Accommodation Lead",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Wing separation and security staffing inspection required before allocating mixed-gender contingents.",
    impact_if_changed: "Hostel allocation engine restricts female contingent members to campus hostels until certified.",
    is_placeholder: true,
  },
  {
    id: "asmp-20",
    name: "equipment_default_quantity",
    category: "Schedule",
    current_value: "1",
    unit: "unit",
    source: "Logistics Standard",
    owner: "Logistics Manager",
    last_updated: "2026-10-29 15:00",
    updated_by: "Logistics Manager",
    reason: "Fallback quantity when technical rider omits amplifier or microphone count.",
    impact_if_changed: "Under-provisioning triggers emergency stage procurement.",
    is_placeholder: false,
  },
  {
    id: "asmp-21",
    name: "shuttle_travel_min",
    category: "Transport",
    current_value: "25",
    unit: "minutes",
    source: "FestOS Seed",
    owner: "Logistics Manager",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Off-peak travel time estimate between IIM Indore campus and Rau bypass hotels.",
    impact_if_changed: "Peak traffic during evening rush hour expands to 45 min; affects contingent arrival to dinner.",
    is_placeholder: true,
  },
  {
    id: "asmp-22",
    name: "transport_hours",
    category: "Transport",
    current_value: "06:00-22:00",
    source: "FestOS Seed",
    owner: "Logistics Manager",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Standard daytime shuttle operations. Late-night shuttles require security escort addendum.",
    impact_if_changed: "Extending hours adds second-shift driver overtime costs.",
    is_placeholder: true,
  },
  {
    id: "asmp-23",
    name: "accom_plan_c_weights",
    category: "Accommodation",
    current_value: "cohesion 0.5, cost 0.3, travel 0.2",
    source: "FestOS Algorithm Spec",
    owner: "Accommodation Lead",
    last_updated: "2026-10-30 08:00",
    updated_by: "System Initializer",
    reason: "Placeholder weights for balanced Plan C solver. Awaiting calibration against contingent sizes.",
    impact_if_changed: "Re-balances contingent room clustering against external hotel expenditure.",
    is_placeholder: true,
  },
  {
    id: "asmp-24",
    name: "include_leaders_escorts_in_demand",
    category: "Accommodation",
    current_value: "true",
    source: "FESTOS_CONTEXT Section 10",
    owner: "Accommodation Lead",
    last_updated: "2026-10-29 10:00",
    updated_by: "Accommodation Lead",
    reason: "Faculty escorts and student contingent leaders occupy dedicated bed inventory.",
    impact_if_changed: "Excluding them creates an immediate 76-bed shortage upon contingent arrival.",
    is_placeholder: false,
  },
  {
    id: "asmp-25",
    name: "count_unknown_accommodation_as_possible",
    category: "Accommodation",
    current_value: "true",
    source: "FESTOS_CONTEXT Section 10",
    owner: "Accommodation Lead",
    last_updated: "2026-10-29 10:00",
    updated_by: "Accommodation Lead",
    reason: "Confirmed and possible demand are reported separately so ops team can hedge contingent buffer.",
    impact_if_changed: "Omitting possible demand under-provisions external hotel block reserve.",
    is_placeholder: false,
  },
];

const INITIAL_HISTORY: AssumptionHistoryEntry[] = [
  {
    id: "hist-1",
    assumption_name: "cleaning_buffer_minutes",
    previous_value: "60",
    new_value: "180",
    updated_at: "2026-10-30 09:15",
    updated_by: "Accommodation Lead",
    reason: "Hostel housekeeping staff feedback during rehearsal dry-run indicated 60 min was insufficient for linen turnover.",
  },
  {
    id: "hist-2",
    assumption_name: "venue_travel_min",
    previous_value: "10",
    new_value: "15",
    updated_at: "2026-10-29 16:45",
    updated_by: "Logistics Manager",
    reason: "Measured walking distance between Convocation Hall and Sports Complex is 1.1 km.",
  },
];

export const AssumptionsPage: React.FC = () => {
  const { addToast } = useToast();
  const [assumptions, setAssumptions] = useState<AssumptionRecord[]>(SEEDED_ASSUMPTIONS);
  const [history, setHistory] = useState<AssumptionHistoryEntry[]>(INITIAL_HISTORY);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [placeholderOnly, setPlaceholderOnly] = useState<boolean>(false);

  // Edit State
  const [selectedAssumption, setSelectedAssumption] = useState<AssumptionRecord | null>(null);
  const [editValue, setEditValue] = useState("");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
  const [historyTargetAssumption, setHistoryTargetAssumption] = useState<string | null>(null);

  // Filtered Assumptions
  const filteredAssumptions = assumptions.filter((item) => {
    if (placeholderOnly && !item.is_placeholder) return false;
    if (categoryFilter !== "ALL" && item.category !== categoryFilter) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.name.toLowerCase().includes(q) ||
      item.owner.toLowerCase().includes(q) ||
      item.source.toLowerCase().includes(q) ||
      item.reason.toLowerCase().includes(q) ||
      item.impact_if_changed.toLowerCase().includes(q)
    );
  });

  const placeholderCount = assumptions.filter((a) => a.is_placeholder).length;

  const handleStartEdit = (assumption: AssumptionRecord) => {
    setSelectedAssumption(assumption);
    setEditValue(assumption.current_value);
    setIsConfirmOpen(true);
  };

  const handleConfirmEdit = async (reason: string) => {
    if (!selectedAssumption) return;

    const previousValue = selectedAssumption.current_value;
    const nowStr = new Date().toISOString().replace("T", " ").substring(0, 16);

    // Update assumption
    setAssumptions((prev) =>
      prev.map((item) => {
        if (item.id === selectedAssumption.id) {
          return {
            ...item,
            current_value: editValue,
            last_updated: nowStr,
            updated_by: "Festival Director",
            reason: reason,
            is_placeholder: editValue === "NULL" || editValue === "UNVERIFIED" || editValue.includes("PENDING"),
          };
        }
        return item;
      })
    );

    // Record history
    const newEntry: AssumptionHistoryEntry = {
      id: `hist-${Date.now()}`,
      assumption_name: selectedAssumption.name,
      previous_value: previousValue,
      new_value: editValue,
      updated_at: nowStr,
      updated_by: "Festival Director",
      reason: reason,
    };
    setHistory((prev) => [newEntry, ...prev]);

    setIsConfirmOpen(false);
    setSelectedAssumption(null);

    addToast({
      title: "Assumption Updated & Audited",
      message: `Updated '${selectedAssumption.name}' to '${editValue}'. Rationale recorded in audit trail.`,
      type: "success",
    });
  };

  const openHistory = (assumptionName?: string) => {
    setHistoryTargetAssumption(assumptionName || null);
    setIsHistoryDrawerOpen(true);
  };

  const filteredHistory = historyTargetAssumption
    ? history.filter((h) => h.assumption_name === historyTargetAssumption)
    : history;

  const columns: Column<AssumptionRecord>[] = [
    {
      key: "name",
      header: "Assumption Key",
      sortable: true,
      render: (row) => (
        <div>
          <div className="font-mono text-xs font-semibold text-white flex items-center gap-1.5">
            {row.name}
            {row.is_placeholder && (
              <Badge variant="outline" className="border-amber-500/40 text-amber-300 text-[10px] py-0 px-1.5">
                UNVERIFIED
              </Badge>
            )}
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">{row.category}</div>
        </div>
      ),
    },
    {
      key: "current_value",
      header: "Current Value",
      render: (row) => (
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-white bg-slate-900 border border-slate-700/60 rounded px-2 py-0.5 text-xs font-mono">
            {row.current_value} {row.unit && <span className="text-slate-400 font-sans text-[11px]">{row.unit}</span>}
          </span>
        </div>
      ),
    },
    {
      key: "owner",
      header: "Owner & Source",
      render: (row) => (
        <div>
          <div className="text-xs text-slate-200 font-medium">{row.owner}</div>
          <div className="text-[11px] text-slate-400 truncate max-w-[140px]">{row.source}</div>
        </div>
      ),
    },
    {
      key: "last_updated",
      header: "Last Updated",
      sortable: true,
      render: (row) => (
        <div className="text-xs text-slate-400">
          <div>{row.last_updated}</div>
          <div className="text-[10px] text-slate-500">by {row.updated_by}</div>
        </div>
      ),
    },
    {
      key: "reason",
      header: "Rationale & Impact If Changed",
      render: (row) => (
        <div className="max-w-md space-y-1 text-xs">
          <p className="text-slate-300 line-clamp-2">
            <span className="text-slate-500 font-medium">Why: </span>
            {row.reason}
          </p>
          <p className="text-indigo-300/90 text-[11px] line-clamp-2">
            <span className="text-indigo-400 font-medium">Impact: </span>
            {row.impact_if_changed}
          </p>
        </div>
      ),
    },
    {
      key: "actions",
      header: "Action",
      render: (row) => (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs border-slate-700 hover:bg-slate-800"
            onClick={() => handleStartEdit(row)}
            data-testid={`edit-assumption-${row.name}`}
          >
            <Edit2 className="h-3 w-3 mr-1 text-slate-400" />
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 text-xs text-slate-400 hover:text-white"
            onClick={() => openHistory(row.name)}
            title="View revision audit trail"
          >
            <History className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            Operational Assumptions Register
            <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 text-xs font-normal">
              Seeded & Verifiable
            </Badge>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            FestOS rule: Assumptions are visible, editable, owned, and sourced. Heuristics are never hidden in code.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => openHistory()}
            className="border-slate-700 text-slate-300 hover:bg-slate-800 text-xs"
          >
            <History className="h-4 w-4 mr-1.5 text-indigo-400" />
            Full Audit History ({history.length})
          </Button>
        </div>
      </div>

      {/* Persistent Banner for Placeholder/Unverified Assumptions */}
      {placeholderCount > 0 && (
        <div
          data-testid="unverified-assumptions-banner"
          className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 shadow-sm flex items-start gap-3.5"
        >
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-amber-200 uppercase tracking-wide">
                Active Heuristic Notice: {placeholderCount} Unverified Assumptions in Use
              </span>
              <Badge variant="solid" className="bg-amber-500/20 text-amber-300 text-[10px]">
                ACTION REQUIRED
              </Badge>
            </div>
            <p className="text-amber-300/90 mt-1">
              Optimization engines (Accommodation Plan C, Shuttle Fleet scheduler, and Budget allocation) are running
              with placeholder defaults. The Festival Director or Module Leads must calibrate and confirm these values
              before final lock.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20 text-xs shrink-0"
            onClick={() => setPlaceholderOnly(!placeholderOnly)}
          >
            {placeholderOnly ? "Show All Assumptions" : "Filter Unverified Only"}
          </Button>
        </div>
      )}

      {/* Surface the Three Open Decisions */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            Top Three Open Operational Decisions
          </h2>
          <span className="text-xs text-slate-400">Section 10 & 13 Governance Mandate</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Decision 1: External Accommodation Budget */}
          <Card className="border-amber-500/30 bg-[#111827]/90 hover:border-amber-500/50 transition-colors">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <DollarSign className="h-3.5 w-3.5" />
                  Decision 1: Budget Ceiling
                </span>
                <Badge variant="outline" className="border-amber-500/40 text-amber-300 text-[10px]">
                  UNSET
                </Badge>
              </div>
              <CardTitle className="text-sm text-white mt-1">external_budget_inr</CardTitle>
              <CardDescription className="text-xs text-slate-300">
                Off-campus hotel room expenditure ceiling (INR)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-0 text-xs">
              <p className="text-slate-400 text-[11px]">
                Currently <strong>NULL</strong>. Accommodation engine runs in budget-unset mode, unable to prune
                over-budget properties.
              </p>
              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300">
                <span className="text-indigo-400 font-medium">Impact: </span>
                Setting this unlocks Plan B (cost-first) and Plan C (balanced) optimization curves.
              </div>
              <Button
                size="sm"
                className="w-full bg-amber-600/80 hover:bg-amber-600 text-white text-xs h-8"
                onClick={() => {
                  const asmp = assumptions.find((a) => a.name === "external_budget_inr");
                  if (asmp) handleStartEdit(asmp);
                }}
              >
                Set Director Budget
              </Button>
            </CardContent>
          </Card>

          {/* Decision 2: Late-Arrival Policy */}
          <Card className="border-indigo-500/30 bg-[#111827]/90 hover:border-indigo-500/50 transition-colors">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  Decision 2: Arrival Grace
                </span>
                <Badge variant="outline" className="border-indigo-500/40 text-indigo-300 text-[10px]">
                  PENDING
                </Badge>
              </div>
              <CardTitle className="text-sm text-white mt-1">late_arrival_policy</CardTitle>
              <CardDescription className="text-xs text-slate-300">
                Curfew bypass and Day 2 wildcard qualification
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-0 text-xs">
              <p className="text-slate-400 text-[11px]">
                Currently <strong>PENDING_DIRECTOR_DECISION</strong>. Flight delays past 22:00 currently require
                manual override approval.
              </p>
              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300">
                <span className="text-indigo-400 font-medium">Impact: </span>
                Options: <code>AUTO_BUFFER_ROOMS</code>, <code>WILDCARD_QUALIFIED</code>, or <code>STRICT_CURFEW</code>.
              </div>
              <Button
                size="sm"
                className="w-full bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs h-8"
                onClick={() => {
                  const asmp = assumptions.find((a) => a.name === "late_arrival_policy");
                  if (asmp) handleStartEdit(asmp);
                }}
              >
                Decide Policy Rule
              </Button>
            </CardContent>
          </Card>

          {/* Decision 3: Shuttle Fleet & Transit Assumptions */}
          <Card className="border-sky-500/30 bg-[#111827]/90 hover:border-sky-500/50 transition-colors">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
                  <Bus className="h-3.5 w-3.5" />
                  Decision 3: Transit Sizing
                </span>
                <Badge variant="outline" className="border-sky-500/40 text-sky-300 text-[10px]">
                  HEURISTIC
                </Badge>
              </div>
              <CardTitle className="text-sm text-white mt-1">shuttle_capacity_seats</CardTitle>
              <CardDescription className="text-xs text-slate-300">
                Fleet size, capacity, and route travel duration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pt-0 text-xs">
              <p className="text-slate-400 text-[11px]">
                Currently <strong>12 seats / 3 vehicles / 25 min</strong>. Arbitrary placeholder numbers from concept
                note.
              </p>
              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-[11px] text-slate-300">
                <span className="text-indigo-400 font-medium">Impact: </span>
                Affects 740 external contingent beds moving to campus for breakfast and events.
              </div>
              <Button
                size="sm"
                className="w-full bg-sky-600/80 hover:bg-sky-600 text-white text-xs h-8"
                onClick={() => {
                  const asmp = assumptions.find((a) => a.name === "shuttle_capacity_seats");
                  if (asmp) handleStartEdit(asmp);
                }}
              >
                Calibrate Fleet Specs
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Assumptions Register Table & Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <CardTitle className="text-base text-white">Full Assumptions Register</CardTitle>
              <CardDescription className="text-xs">
                All 25 active system heuristics with ownership, reason, and operational downstream impact.
              </CardDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="relative w-48">
                <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter keys / text..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1 bg-slate-900 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Categories</option>
                <option value="Accommodation">Accommodation</option>
                <option value="Transport">Transport</option>
                <option value="Schedule">Schedule</option>
                <option value="Finance">Finance</option>
                <option value="General">General</option>
              </select>

              <Button
                size="sm"
                variant={placeholderOnly ? "primary" : "outline"}
                className="text-xs h-7 border-slate-700"
                onClick={() => setPlaceholderOnly(!placeholderOnly)}
              >
                <Filter className="h-3 w-3 mr-1" />
                {placeholderOnly ? "Unverified (Active)" : "All Statuses"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={filteredAssumptions}
            total={filteredAssumptions.length}
            keyExtractor={(row) => row.id}
          />
        </CardContent>
      </Card>

      {/* Edit Modal with ConfirmWithReason */}
      {selectedAssumption && (
        <ConfirmWithReason
          isOpen={isConfirmOpen}
          onClose={() => {
            setIsConfirmOpen(false);
            setSelectedAssumption(null);
          }}
          title={`Modify Assumption: ${selectedAssumption.name}`}
          description={`FestOS requires an operational reason for changing '${selectedAssumption.name}'. Current value: ${selectedAssumption.current_value}.`}
          confirmText="Save & Record Audit Log"
          placeholder="e.g. Calibrated based on Indore transport vendor contract signed for 40-seat coach buses..."
          riskLevel={selectedAssumption.isOpenDecision ? "CRITICAL" : "HIGH"}
          onConfirm={handleConfirmEdit}
        >
          <div className="mb-4 space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                New Target Value {selectedAssumption.unit && `(${selectedAssumption.unit})`}
              </label>
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
                placeholder="Enter verified value..."
                data-testid="input-edit-assumption-value"
                autoFocus
              />
            </div>
            <div className="rounded-lg bg-slate-900/60 p-3 border border-slate-800 text-xs space-y-1">
              <div className="text-slate-400">
                <strong>Current Owner:</strong> {selectedAssumption.owner}
              </div>
              <div className="text-slate-400">
                <strong>Source:</strong> {selectedAssumption.source}
              </div>
              <div className="text-indigo-300">
                <strong>Downstream Impact:</strong> {selectedAssumption.impact_if_changed}
              </div>
            </div>
          </div>
        </ConfirmWithReason>
      )}

      {/* History Drawer */}
      <Drawer
        isOpen={isHistoryDrawerOpen}
        onClose={() => setIsHistoryDrawerOpen(false)}
        title={
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-indigo-400" />
            <span>
              {historyTargetAssumption
                ? `History: ${historyTargetAssumption}`
                : "Assumptions Mutation Audit Log"}
            </span>
          </div>
        }
        description="Immutable record of all heuristic modifications with recorded operational justifications."
        width="max-w-xl"
      >
        <div className="p-6 space-y-4">
          {filteredHistory.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              <HelpCircle className="h-8 w-8 mx-auto mb-2 text-slate-500" />
              No modifications recorded yet for this assumption.
            </div>
          ) : (
            filteredHistory.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-white">{item.assumption_name}</span>
                  <span className="text-[11px] text-slate-400">{item.updated_at}</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="line-through text-rose-400/80 bg-rose-950/40 px-1.5 py-0.5 rounded border border-rose-800/40">
                    {item.previous_value}
                  </span>
                  <span className="text-slate-400">➔</span>
                  <span className="text-emerald-300 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-800/40 font-bold">
                    {item.new_value}
                  </span>
                  <span className="text-slate-400 font-sans ml-auto text-[11px]">by {item.updated_by}</span>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80 text-slate-300 text-xs">
                  <span className="text-slate-500 font-medium">Recorded Reason: </span>
                  {item.reason}
                </div>
              </div>
            ))
          )}
        </div>
      </Drawer>
    </div>
  );
};

export default AssumptionsPage;
