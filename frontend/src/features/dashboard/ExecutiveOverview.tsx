import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Users,
  ShieldAlert,
  Flame,
  CheckCircle2,
  BellOff,
  ArrowUpRight,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
  Button,
  Modal,
  Drawer,
  useToast,
} from "../../components/ui";
import {
  RoleVariant,
  SpecKpiMetric,
  AttentionItem,
  HeatmapCell,
  DashboardMetricsResponse,
} from "./types";
import { api } from "../../api/client";

export const ExecutiveOverview: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [activeRole, setActiveRole] = useState<RoleVariant>("DIRECTOR");
  const [snoozeModalItem, setSnoozeModalItem] = useState<AttentionItem | null>(null);
  const [snoozeReason, setSnoozeReason] = useState("");
  const [snoozeDuration, setSnoozeDuration] = useState("60");
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [drilldownCell, setDrilldownCell] = useState<HeatmapCell | null>(null);

  // 1. Fetch KPI metrics
  const { data: metricsData, isLoading: metricsLoading } = useQuery<{ data: DashboardMetricsResponse }>({
    queryKey: ["dashboard", "metrics", activeRole],
    queryFn: async () => {
      return api.get(`/api/v1/dashboard/metrics?role=${activeRole}`);
    },
  });

  // 2. Fetch Attention Queue
  const { data: attentionData } = useQuery<{ data: { items: AttentionItem[]; total: number } }>({
    queryKey: ["dashboard", "attention"],
    queryFn: async () => {
      return api.get("/api/v1/dashboard/attention");
    },
  });

  // 3. Fetch Risk Heatmap
  const { data: heatmapData } = useQuery<{ data: { cells: HeatmapCell[]; totalRisks: number } }>({
    queryKey: ["dashboard", "heatmap"],
    queryFn: async () => {
      return api.get("/api/v1/dashboard/heatmap");
    },
  });

  // Mutation to snooze/acknowledge attention item
  const snoozeMutation = useMutation({
    mutationFn: async ({
      id,
      reason,
      minutes,
      acknowledged,
    }: {
      id: string;
      reason: string;
      minutes: number;
      acknowledged: boolean;
    }) => {
      return api.post(`/api/v1/dashboard/attention/${id}/snooze`, {
        reason,
        minutes,
        acknowledged,
      });
    },
    onSuccess: (_, variables) => {
      addToast({
        type: "success",
        title: variables.acknowledged ? "Alert Acknowledged" : "Alert Snoozed",
        message: `Operational rationale recorded. Attention queue refreshed.`,
      });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "attention"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "heatmap"] });
      setSnoozeModalItem(null);
      setSnoozeReason("");
    },
    onError: () => {
      addToast({
        type: "error",
        title: "Action Failed",
        message: "Failed to update attention item status.",
      });
    },
  });

  const m = ((metricsData as any)?.data || metricsData) as DashboardMetricsResponse | undefined;
  const attentionItems: AttentionItem[] = (attentionData as any)?.items || (attentionData as any)?.data?.items || [];
  const heatmapCells: HeatmapCell[] = (heatmapData as any)?.cells || (heatmapData as any)?.data?.cells || [];

  // Grouped spec KPI metrics for tiles
  const specKpis: SpecKpiMetric[] = m
    ? [
        {
          id: "kpi_participants",
          label: "Participants",
          value: `${m.checked_in.toLocaleString()} / ${m.total_participants.toLocaleString()}`,
          subValue: `${m.raw_participants} raw vs 2,400 narrative (${m.pending_arrivals} pending)`,
          category: "participants",
          status: m.pending_arrivals > 1000 ? "WARNING" : "GOOD",
          moduleRoute: "/participants",
          contextExplanation: "Checked-in vs Canonical registered participants.",
        },
        {
          id: "kpi_accommodation",
          label: "Beds Occupancy",
          value: `${m.occupancy_pct}%`,
          subValue: `${m.unplaced_participants} unplaced · ${m.available_beds} beds left`,
          category: "accommodation",
          status: m.unplaced_participants > 0 ? "CRITICAL" : "GOOD",
          moduleRoute: "/accommodation",
          contextExplanation: "710 campus + 740 external beds across 6 properties.",
        },
        {
          id: "kpi_schedule",
          label: "Active Sessions & Venues",
          value: `${m.active_sessions} Active`,
          subValue: `${m.open_conflicts} venue conflict${m.open_conflicts !== 1 ? "s" : ""}`,
          category: "events",
          status: m.open_conflicts > 0 ? "WARNING" : "GOOD",
          moduleRoute: "/events",
          contextExplanation: "Real-time schedule session tracking across 9 venues.",
        },
        {
          id: "kpi_logistics",
          label: "Critical Equipment",
          value: `${m.equipment_availability}% Avail`,
          subValue: `${m.equipment_in_transit} in transit · ${m.equipment_under_repair} repair`,
          category: "logistics",
          status: m.equipment_under_repair > 0 ? "WARNING" : "GOOD",
          moduleRoute: "/logistics",
          contextExplanation: "PA systems, consoles, and backup generator readiness.",
        },
        {
          id: "kpi_merchandise",
          label: "Merchandise Kits",
          value: `${m.merch_issued.toLocaleString()} Issued`,
          subValue: `${m.merchandise_stock} kitbags on hand`,
          category: "merchandise",
          status: m.merchandise_stock < 100 ? "WARNING" : "GOOD",
          moduleRoute: "/merchandise",
          contextExplanation: "Kitbag distribution at main concourse check-in.",
        },
        {
          id: "kpi_food",
          label: "Food & Catering",
          value: m.vendor_status,
          subValue: `${m.uncovered_meals} deficit · ${m.food_coverage_gaps} gap slots`,
          category: "food",
          status: m.uncovered_meals > 0 ? "CRITICAL" : "GOOD",
          moduleRoute: "/food",
          contextExplanation: "Vendor stalls and special Jain/Vegan dietary buffers.",
        },
        {
          id: "kpi_staff",
          label: "Volunteer Shifts",
          value: `${m.staff_availability} on Shift`,
          subValue: `${m.peak_staffing_gap} gap slots · 48 core team`,
          category: "staff",
          status: m.peak_staffing_gap > 0 ? "WARNING" : "GOOD",
          moduleRoute: "/staff",
          contextExplanation: "Roster coverage vs hourly venue staffing demand.",
        },
        {
          id: "kpi_governance",
          label: "Active Disruptions",
          value: `${m.open_incidents} Open`,
          subValue: `${m.pending_approvals} approvals · ${m.active_overrides} overrides`,
          category: "governance",
          status: m.open_incidents > 0 ? "CRITICAL" : "GOOD",
          moduleRoute: "/incidents",
          contextExplanation: "Disruptions managed under ChangeService governance.",
        },
      ]
    : [];

  const handleSnoozeSubmit = () => {
    if (!snoozeModalItem) return;
    if (!snoozeReason.trim()) {
      addToast({
        type: "error",
        title: "Reason Required",
        message: "Under FestOS principles, every snooze or acknowledgment must record an operational rationale.",
      });
      return;
    }
    snoozeMutation.mutate({
      id: snoozeModalItem.id,
      reason: snoozeReason.trim(),
      minutes: Number(snoozeDuration),
      acknowledged: isAcknowledging,
    });
  };

  return (
    <div className="space-y-6" data-testid="executive-overview-workspace">
      {/* 1. Header & Role Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">FestOS Command Overview</h1>
            <Badge variant="solid" status="SUCCESS">
              LIVE STATE
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            EPINOIA 2026 (Aarohan Fest, IIM Indore) — Operational Readiness & Exceptions Queue
          </p>
        </div>

        {/* Role Presets */}
        <div className="flex items-center gap-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1 overflow-x-auto" data-testid="role-switcher">
          {(
            [
              { id: "DIRECTOR", label: "Director" },
              { id: "ACCOMMODATION_LEAD", label: "Accommodation" },
              { id: "EVENT_LEAD", label: "Events" },
              { id: "LOGISTICS_MANAGER", label: "Logistics" },
              { id: "FOOD_OPS_MANAGER", label: "Food Ops" },
              { id: "FINANCE_MANAGER", label: "Finance" },
              { id: "VOLUNTEER", label: "Volunteer Mobile" },
            ] as const
          ).map((role) => (
            <button
              key={role.id}
              data-testid={`role-tab-${role.id}`}
              onClick={() => setActiveRole(role.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
                activeRole === role.id
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              {role.label}
            </button>
          ))}
        </div>
      </div>

      {/* VOLUNTEER MOBILE HOME VARIANT */}
      {activeRole === "VOLUNTEER" ? (
        <div className="max-w-xl mx-auto space-y-4" data-testid="volunteer-mobile-view">
          <Card className="border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 to-slate-900">
            <CardHeader>
              <div className="flex items-center justify-between">
                <Badge variant="solid" status="SUCCESS">
                  CURRENT ON-DUTY SHIFT
                </Badge>
                <span className="text-xs text-slate-400 font-mono">12:00 – 14:00</span>
              </div>
              <CardTitle className="text-xl text-white mt-2">Registration Concourse Desk</CardTitle>
              <CardDescription className="text-indigo-200">
                Main Concourse Wing A · Check-in scanner duty
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/80 text-sm">
                <span className="text-slate-400">Assigned Shift Lead:</span>
                <span className="font-medium text-white">Aarav Sharma (+91 98765 43210)</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/80 text-sm">
                <span className="text-slate-400">Consecutive Hours Worked:</span>
                <span className="font-semibold text-emerald-400">2.5 hrs (Normal)</span>
              </div>
              <div className="pt-2 flex gap-2">
                <Button
                  variant="primary"
                  className="w-full justify-center"
                  onClick={() => navigate("/checkin")}
                >
                  Open QR Check-in Desk
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-center"
                  onClick={() => navigate("/staff")}
                >
                  View Shift Roster
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/60">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold text-white">Volunteer Checklist</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex items-center gap-2 p-2 rounded bg-slate-800/50 text-slate-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Verify contingent ID badge before handing over festival kitbag</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded bg-slate-800/50 text-slate-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Escort minor participants with external hotel tags to transport desk</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded bg-slate-800/50 text-slate-300">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Report any missing luggage directly to Control Room (Intercom #4)</span>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <>
          {/* 2. Canonical Spec Metric KPI Tiles (Clickable into Modules) */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Festival-Wide Canonical Metrics (Click to Inspect)
              </h2>
              <span className="text-xs text-slate-500 font-mono">
                {metricsLoading ? "Refreshing..." : "15s auto-cached · event-invalidated"}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" data-testid="kpi-tiles-grid">
              {specKpis.map((kpi) => (
                <div
                  key={kpi.id}
                  data-testid={`kpi-tile-${kpi.id}`}
                  onClick={() => navigate(kpi.moduleRoute)}
                  className="group relative cursor-pointer rounded-xl border border-slate-800 bg-slate-900/80 p-4 shadow-sm hover:border-indigo-500/50 hover:bg-slate-800/70 transition-all"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-400">{kpi.label}</span>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
                  </div>
                  <div className="text-2xl font-extrabold text-white mt-1.5 tracking-tight">
                    {kpi.value}
                  </div>
                  {kpi.subValue && (
                    <div className="text-xs text-slate-400 mt-1 truncate">
                      {kpi.subValue}
                    </div>
                  )}
                  <div className="mt-2.5 flex items-center justify-between">
                    <Badge
                      variant="outline"
                      status={
                        kpi.status === "CRITICAL"
                          ? "REJECTED"
                          : kpi.status === "WARNING"
                          ? "PENDING"
                          : "SUCCESS"
                      }
                    >
                      {kpi.status}
                    </Badge>
                    <span className="text-[11px] text-indigo-400 font-medium group-hover:underline">
                      View module →
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Main Operational Split: Prioritised Attention Queue & Risk Heatmap */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Attention Queue (7 cols): Exceptions First, Ranked strictly by Severity x Urgency x max(people, 1) */}
            <div className="lg:col-span-7 space-y-3" data-testid="attention-queue-section">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-rose-500 animate-pulse" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                    Prioritised Attention Queue ({attentionItems.length})
                  </h2>
                </div>
                <span className="text-xs text-slate-500 font-mono">
                  Ranked by Severity × Urgency × People
                </span>
              </div>

              <div className="space-y-3">
                {attentionItems.length === 0 ? (
                  <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-sm">
                    No active high-severity exceptions detected. All critical systems nominal.
                  </div>
                ) : (
                  attentionItems.map((item, idx) => (
                    <Card
                      key={item.id}
                      data-testid={`attention-item-${item.id}`}
                      className={`border-l-4 transition-all ${
                        item.severity === "CRITICAL"
                          ? "border-l-rose-500 border-slate-800 bg-slate-900/90"
                          : item.severity === "HIGH"
                          ? "border-l-amber-500 border-slate-800 bg-slate-900/80"
                          : "border-l-indigo-500 border-slate-800 bg-slate-900/70"
                      } ${item.isSnoozed ? "opacity-60" : ""}`}
                    >
                      <CardContent className="p-4 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono font-bold text-slate-400">
                              #{idx + 1}
                            </span>
                            <Badge
                              variant="solid"
                              status={
                                item.severity === "CRITICAL"
                                  ? "REJECTED"
                                  : item.severity === "HIGH"
                                  ? "PENDING"
                                  : "SUCCESS"
                              }
                            >
                              {item.severity}
                            </Badge>
                            <Badge variant="outline">
                              Urgency: {item.hoursToImpact <= 1 ? "≤1h" : `≤${item.hoursToImpact}h`}
                            </Badge>
                            <span className="text-xs text-slate-400 flex items-center gap-1 font-medium">
                              <Users className="w-3.5 h-3.5 text-slate-500" />
                              {item.peopleAffected} affected
                            </span>
                            <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              Score: {item.attentionScore}
                            </span>
                          </div>

                          <div className="text-xs font-medium text-slate-400 capitalize">
                            Domain: <strong className="text-slate-200">{item.module}</strong>
                          </div>
                        </div>

                        <div>
                          <h3 className="text-sm font-semibold text-white tracking-tight">
                            {item.title}
                          </h3>
                          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                            {item.explanation}
                          </p>
                        </div>

                        {item.isSnoozed && (
                          <div className="text-xs bg-slate-800/80 border border-slate-700 rounded p-2 text-amber-300 flex items-center justify-between">
                            <span>Snoozed: {item.snoozeReason}</span>
                            <span className="text-[11px] text-slate-400 font-mono">
                              Until {item.snoozedUntil?.substring(11, 16)} UTC
                            </span>
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 gap-2">
                          <Button
                            data-testid={`action-btn-${item.id}`}
                            variant="primary"
                            size="sm"
                            onClick={() => navigate(item.action.route)}
                            className="text-xs font-semibold"
                          >
                            {item.action.label} →
                          </Button>

                          <div className="flex items-center gap-2">
                            <Button
                              data-testid={`snooze-btn-${item.id}`}
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setIsAcknowledging(false);
                                setSnoozeModalItem(item);
                              }}
                              className="text-xs"
                            >
                              <BellOff className="w-3 h-3 mr-1" />
                              Snooze
                            </Button>
                            <Button
                              data-testid={`acknowledge-btn-${item.id}`}
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setIsAcknowledging(true);
                                setSnoozeModalItem(item);
                              }}
                              className="text-xs"
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                              Acknowledge
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </div>

            {/* Risk Heatmap (5 cols): Severity x Time-to-Impact */}
            <div className="lg:col-span-5 space-y-3" data-testid="risk-heatmap-section">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-indigo-400" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-white">
                    Risk Heatmap (Severity × Time)
                  </h2>
                </div>
                <span className="text-xs text-slate-500 font-mono">Bubble = People · Opacity = Certainty</span>
              </div>

              <Card className="border-slate-800 bg-slate-900/90 p-4">
                <div className="text-xs text-slate-400 mb-3 leading-relaxed">
                  Click any cell to drill down into active risk items, uncertainty metrics, and resolution actions.
                </div>

                {/* 2D Matrix Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr>
                        <th className="p-1.5 text-left text-slate-500 font-medium">Sev \ Horizon</th>
                        <th className="p-1.5 text-center text-slate-400 font-medium">≤1h</th>
                        <th className="p-1.5 text-center text-slate-400 font-medium">1-4h</th>
                        <th className="p-1.5 text-center text-slate-400 font-medium">4-12h</th>
                        <th className="p-1.5 text-center text-slate-400 font-medium">12-24h</th>
                        <th className="p-1.5 text-center text-slate-400 font-medium">&gt;24h</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => {
                        return (
                          <tr key={sev} className="border-t border-slate-800">
                            <td className="p-2 font-bold text-slate-300">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] ${
                                  sev === "CRITICAL"
                                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                                    : sev === "HIGH"
                                    ? "bg-amber-950 text-amber-300 border border-amber-800"
                                    : "bg-indigo-950 text-indigo-300 border border-indigo-800"
                                }`}
                              >
                                {sev}
                              </span>
                            </td>
                            {(["<=1h", "1-4h", "4-12h", "12-24h", ">24h"] as const).map((tw) => {
                              const cell = heatmapCells.find(
                                (c) => c.severity === sev && c.timeWindow === tw
                              );
                              const count = cell ? cell.itemCount : 0;
                              const people = cell ? cell.totalPeopleAffected : 0;
                              const uncertainty = cell ? cell.avgUncertainty : 0;
                              const certainty = 1 - uncertainty;

                              return (
                                <td
                                  key={tw}
                                  data-testid={`heatmap-cell-${sev}-${tw}`}
                                  onClick={() => cell && cell.itemCount > 0 && setDrilldownCell(cell)}
                                  className={`p-2 text-center transition-all ${
                                    count > 0
                                      ? "cursor-pointer hover:scale-105"
                                      : "text-slate-700"
                                  }`}
                                >
                                  {count > 0 ? (
                                    <div
                                      style={{
                                        opacity: Math.max(0.4, certainty),
                                      }}
                                      className={`inline-flex flex-col items-center justify-center rounded-lg border font-mono ${
                                        sev === "CRITICAL"
                                          ? "bg-rose-900/60 border-rose-500/80 text-rose-100 shadow-rose-950"
                                          : sev === "HIGH"
                                          ? "bg-amber-900/60 border-amber-500/80 text-amber-100 shadow-amber-950"
                                          : "bg-indigo-900/50 border-indigo-500/80 text-indigo-100 shadow-indigo-950"
                                      } ${
                                        people > 100
                                          ? "w-12 h-12 text-sm"
                                          : people > 20
                                          ? "w-10 h-10 text-xs"
                                          : "w-8 h-8 text-xs"
                                      }`}
                                      title={`${count} items, ${people} people affected. Click to drill-down.`}
                                    >
                                      <span className="font-bold leading-none">{count}</span>
                                      <span className="text-[9px] text-slate-300 mt-0.5 leading-none">
                                        {people}p
                                      </span>
                                    </div>
                                  ) : (
                                    <span className="text-slate-700 text-xs">—</span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Heatmap Legend */}
                <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded bg-rose-600" />
                    <span>Critical</span>
                    <div className="w-2.5 h-2.5 rounded bg-amber-600 ml-2" />
                    <span>High</span>
                    <div className="w-2.5 h-2.5 rounded bg-indigo-600 ml-2" />
                    <span>Medium</span>
                  </div>
                  <span>Size = Affected People · Opacity = Certainty</span>
                </div>
              </Card>

              {/* Fast Module Shortcuts */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/scenarios")}
                  className="justify-between"
                >
                  <span>Scenario Simulator</span>
                  <span>→</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/premortem")}
                  className="justify-between"
                >
                  <span>Fest Pre-Mortem</span>
                  <span>→</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/unknowns")}
                  className="justify-between"
                >
                  <span>Unknowns Burn-down</span>
                  <span>→</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/decisions")}
                  className="justify-between"
                >
                  <span>Decision Log</span>
                  <span>→</span>
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* 4. Snooze / Acknowledge Modal */}
      {snoozeModalItem && (
        <Modal
          isOpen={true}
          onClose={() => setSnoozeModalItem(null)}
          title={isAcknowledging ? "Acknowledge Operational Exception" : "Snooze Operational Alert"}
          size="md"
        >
          <div className="space-y-4" data-testid="snooze-modal">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1">
              <div className="font-semibold text-white">{snoozeModalItem.title}</div>
              <div className="text-slate-400">
                Affects {snoozeModalItem.peopleAffected} participants under {snoozeModalItem.module} domain.
              </div>
            </div>

            {!isAcknowledging && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Snooze Duration
                </label>
                <select
                  value={snoozeDuration}
                  onChange={(e) => setSnoozeDuration(e.target.value)}
                  className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="30">30 minutes</option>
                  <option value="60">1 hour (Recommended)</option>
                  <option value="120">2 hours</option>
                  <option value="240">4 hours</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Mandatory Operational Rationale <span className="text-rose-400">*</span>
              </label>
              <textarea
                data-testid="snooze-reason-input"
                rows={3}
                placeholder="Under FestOS principles, record explicit reason for deferral or acknowledgment..."
                value={snoozeReason}
                onChange={(e) => setSnoozeReason(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setSnoozeModalItem(null)}>
                Cancel
              </Button>
              <Button
                data-testid="confirm-snooze-btn"
                variant="primary"
                size="sm"
                onClick={handleSnoozeSubmit}
                disabled={!snoozeReason.trim()}
              >
                {isAcknowledging ? "Confirm Acknowledgment" : "Confirm Snooze"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* 5. Heatmap Cell Drilldown Drawer */}
      {drilldownCell && (
        <Drawer
          isOpen={true}
          onClose={() => setDrilldownCell(null)}
          title={`Risks: ${drilldownCell.severity} Severity · Window ${drilldownCell.timeWindow}`}
          width="max-w-md"
        >
          <div className="space-y-4" data-testid="drilldown-drawer">
            <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800">
              <span>{drilldownCell.items.length} Active Incidents / Exceptions</span>
              <span>{drilldownCell.totalPeopleAffected} Total People Affected</span>
            </div>

            <div className="space-y-3">
              {drilldownCell.items.map((it) => (
                <div
                  key={it.id}
                  className="p-3 rounded-lg border border-slate-800 bg-slate-900/80 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">{it.module}</Badge>
                    <span className="font-mono text-slate-400">Score: {it.attentionScore}</span>
                  </div>
                  <div className="font-semibold text-white">{it.title}</div>
                  <p className="text-slate-400 leading-relaxed">{it.explanation}</p>
                  <div className="pt-2 flex justify-between items-center">
                    <span className="text-[11px] text-slate-500">
                      Uncertainty: {Math.round(it.uncertainty * 100)}%
                    </span>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => {
                        setDrilldownCell(null);
                        navigate(it.action.route);
                      }}
                      className="text-xs"
                    >
                      {it.action.label} →
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Drawer>
      )}
    </div>
  );
};

export default ExecutiveOverview;
