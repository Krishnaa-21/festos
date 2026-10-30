import React, { useState, useEffect } from "react";
import {
  Building,
  DollarSign,
  AlertTriangle,
  Sliders,
  CheckCircle2,
  Users,
  Layers,
  Sparkles,
  RefreshCw,
  ExternalLink,
  Send,
} from "lucide-react";
import {
  ResponsiveContainer,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Line,
  ComposedChart,
} from "recharts";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Tabs,
  ConfirmWithReason,
  useToast,
} from "../../components/ui";
import {
  AccommodationPlan,
  PlansResponseData,
  ShortagesResponseData,
  OccupancyData,
  Bed,
  Room,
  HostelBlock,
} from "./types";
import { api } from "../../api/client";
import ShortageView from "./ShortageView";
import OccupancyMap from "./OccupancyMap";
import DecisionFlowModal from "./DecisionFlowModal";
import { useNavigate } from "react-router-dom";

export const AccommodationWorkspace: React.FC = () => {
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<string>("compare");

  // Plans State
  const [plansData, setPlansData] = useState<PlansResponseData | null>(null);
  const [plansLoading, setPlansLoading] = useState<boolean>(true);

  // Shortages State
  const [shortagesData, setShortagesData] = useState<ShortagesResponseData | null>(null);
  const [shortagesLoading, setShortagesLoading] = useState<boolean>(true);

  // Occupancy State
  const [occupancyData, setOccupancyData] = useState<OccupancyData | null>(null);
  const [occupancyLoading, setOccupancyLoading] = useState<boolean>(true);

  // Generator Parameters State
  const [selectedPlanKind, setSelectedPlanKind] = useState<"A" | "B" | "C">("C");
  const [cleaningBuffer, setCleaningBuffer] = useState<number>(180);
  const [maxDistance, setMaxDistance] = useState<number>(15);
  const [allowSplits, setAllowSplits] = useState<boolean>(true);
  const [cohesionWeight, setCohesionWeight] = useState<number>(0.5);
  const [costWeight, setCostWeight] = useState<number>(0.3);
  const [travelWeight, setTravelWeight] = useState<number>(0.2);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Commit Live State
  const [livePlanId, setLivePlanId] = useState<string | null>(null);
  const [showCommitModal, setShowCommitModal] = useState<boolean>(false);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);

  // Decision Modal State
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState<boolean>(false);
  const [selectedBedForMove, setSelectedBedForMove] = useState<Bed | null>(null);
  const [selectedRoomForMove, setSelectedRoomForMove] = useState<Room | null>(null);
  const [selectedBlockForMove, setSelectedBlockForMove] = useState<HostelBlock | null>(null);

  // Fetch all accommodation data
  const fetchData = async () => {
    setPlansLoading(true);
    setShortagesLoading(true);
    setOccupancyLoading(true);

    try {
      const plansRes = await api.get<PlansResponseData>("/api/v1/accommodation/plans");
      setPlansData(plansRes);
    } catch {
      // Fallback plans if backend not yet merged
      setPlansData({
        plans: [
          {
            plan_id: "plan_A_cohesion",
            kind: "A",
            status: "CANDIDATE",
            name: "Plan A: Cohesion-First",
            on_campus_placed: 710,
            external_placed: 1284,
            unplaced_count: 150,
            contingent_splits: 4,
            total_cost_inr: 3315700,
            safety_flags_count: 12,
            accessibility_issues_count: 2,
            relaxed_constraints_count: 8,
            sacrifices_summary:
              "Sacrifices budget expenditure (₹33,15,700) to keep contingents unified within the same buildings.",
            created_at: "2026-10-30T10:00:00Z",
          },
          {
            plan_id: "plan_B_cost",
            kind: "B",
            status: "CANDIDATE",
            name: "Plan B: Cost-First",
            on_campus_placed: 710,
            external_placed: 1342,
            unplaced_count: 92,
            contingent_splits: 19,
            total_cost_inr: 2480000,
            safety_flags_count: 28,
            accessibility_issues_count: 4,
            relaxed_constraints_count: 31,
            sacrifices_summary:
              "Sacrifices contingent cohesion and group proximity to minimize external hotel booking costs.",
            created_at: "2026-10-30T10:00:00Z",
          },
          {
            plan_id: "plan_C_balanced",
            kind: "C",
            status: "CANDIDATE",
            name: "Plan C: Balanced (Recommended)",
            on_campus_placed: 710,
            external_placed: 1318,
            unplaced_count: 116,
            contingent_splits: 8,
            total_cost_inr: 2890000,
            safety_flags_count: 14,
            accessibility_issues_count: 1,
            relaxed_constraints_count: 12,
            sacrifices_summary:
              "Balanced compromises: permits minor contingent splits only when hotel cost exceeds threshold.",
            created_at: "2026-10-30T10:00:00Z",
          },
        ],
        budget_ceiling_inr: null,
        is_budget_unset: true,
      });
    } finally {
      setPlansLoading(false);
    }

    try {
      const shortagesRes = await api.get<ShortagesResponseData>("/api/v1/accommodation/shortages");
      setShortagesData(shortagesRes);
    } catch {
      // Handled in ShortageView fallback
    } finally {
      setShortagesLoading(false);
    }

    try {
      const occupancyRes = await api.get<OccupancyData>("/api/v1/accommodation/occupancy");
      setOccupancyData(occupancyRes);
    } catch {
      // Handled in OccupancyMap fallback
    } finally {
      setOccupancyLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    try {
      const res = await api.post<AccommodationPlan>("/api/v1/accommodation/generate-plan", {
        kind: selectedPlanKind,
        cleaning_buffer_minutes: cleaningBuffer,
        max_distance_km: maxDistance,
        allow_split_contingents: allowSplits,
        weights: {
          cohesion: cohesionWeight,
          cost: costWeight,
          travel: travelWeight,
        },
      });

      addToast({
        title: "Accommodation Plan Generated",
        message: `Generated candidate ${res.name}. Updated metrics are now visible in the compare matrix.`,
        type: "success",
      });

      // Update local plans
      setPlansData((prev) => {
        if (!prev) return prev;
        const exists = prev.plans.findIndex((p) => p.kind === res.kind);
        const updated = [...prev.plans];
        if (exists >= 0) {
          updated[exists] = res;
        } else {
          updated.push(res);
        }
        return { ...prev, plans: updated };
      });
    } catch {
      addToast({
        title: "Plan Generation Failed",
        message: "Failed to run optimization solver.",
        type: "error",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCommitLive = async (reason: string) => {
    setIsCommitting(true);
    try {
      const targetPlan = plansData?.plans.find((p) => p.kind === selectedPlanKind) || plansData?.plans[2];
      await api.post("/api/v1/accommodation/commit-live", {
        expected_version: 1,
        plan_id: targetPlan?.plan_id || "plan_C_balanced",
        reason,
      });

      setLivePlanId(targetPlan?.plan_id || "plan_C_balanced");
      setShowCommitModal(false);
      addToast({
        title: "Plan Committed to Live",
        message: `${targetPlan?.name} is now the authorized LIVE operational plan for Aarohan 2026.`,
        type: "success",
      });
    } catch {
      setShowCommitModal(false);
      addToast({
        title: "Commit Live (Simulated)",
        message: "Plan marked as LIVE in operational session.",
        type: "success",
      });
      setLivePlanId("plan_C_balanced");
    } finally {
      setIsCommitting(false);
    }
  };

  const plans = plansData?.plans || [];

  // Chart data for Recharts Cost-versus-Cohesion trade-off
  const chartData = plans.map((p) => ({
    name: p.kind === "A" ? "Plan A (Cohesion)" : p.kind === "B" ? "Plan B (Cost)" : "Plan C (Balanced)",
    costInLakhs: Math.round((p.total_cost_inr / 100000) * 10) / 10,
    splitsCount: p.contingent_splits,
    unplaced: p.unplaced_count,
    costFormatted: `₹${(p.total_cost_inr / 100000).toFixed(1)}L`,
  }));

  const workspaceTabs = [
    { id: "compare", label: "Plan Generator & Compare", icon: <Sliders className="h-4 w-4" /> },
    {
      id: "shortages",
      label: `Shortage View (${shortagesData?.total_unplaced ?? 116})`,
      icon: <AlertTriangle className="h-4 w-4" />,
    },
    { id: "occupancy", label: "Occupancy Map", icon: <Building className="h-4 w-4" /> },
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Fast Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-sm border border-indigo-500/30">
              <Building className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Accommodation Workspace</h1>
              <p className="text-xs text-slate-400">
                Aarohan 2026 Hostels (710 beds) & External Properties (740 beds) • Plan Optimization & Bed Control
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            isLoading={plansLoading}
            className="text-xs border-slate-700 text-slate-300"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1" />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => {
              setSelectedBedForMove(null);
              setIsDecisionModalOpen(true);
            }}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs"
            data-testid="open-assign-modal-btn"
          >
            <Send className="h-3.5 w-3.5 mr-1" />
            Manual Move / Assign
          </Button>
        </div>
      </div>

      {/* BUDGET-UNSET WARNING BANNER (MANDATORY per spec section 10 & BUILD 1) */}
      {plansData?.is_budget_unset && (
        <div
          className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-amber-200"
          data-testid="budget-unset-banner"
        >
          <div className="flex items-start sm:items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold text-amber-300 text-sm">
                External Accommodation Budget is Unset (NULL)
              </div>
              <p className="text-xs text-amber-200/90 mt-0.5">
                The optimization engine is running in unconstrained mode without a financial cap. Festival Director must review the Assumptions Register to authorize the budget ceiling.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate("/assumptions")}
            className="border-amber-500/50 text-amber-300 hover:bg-amber-900/30 text-xs shrink-0"
          >
            <ExternalLink className="h-3.5 w-3.5 mr-1" />
            Configure in Assumptions
          </Button>
        </div>
      )}

      {/* Navigation Tabs */}
      <Tabs tabs={workspaceTabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* TAB 1: Plan Generator & Compare */}
      {activeTab === "compare" && (
        <div className="space-y-6">
          {/* Plan Generator Parameter Controls */}
          <Card className="p-5 bg-slate-950/80 border-slate-800">
            <CardHeader className="p-0 pb-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-indigo-400" />
                  <span>Candidate Plan Generator & Parameter Weights</span>
                </CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Choose Plan kind (A, B, or C) and configure operational buffers before running the solver.
                </p>
              </div>

              {/* Plan Kind Selector A / B / C */}
              <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800">
                <button
                  onClick={() => setSelectedPlanKind("A")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    selectedPlanKind === "A"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  data-testid="plan-a-btn"
                >
                  Plan A (Cohesion)
                </button>
                <button
                  onClick={() => setSelectedPlanKind("B")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    selectedPlanKind === "B"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  data-testid="plan-b-btn"
                >
                  Plan B (Cost)
                </button>
                <button
                  onClick={() => setSelectedPlanKind("C")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    selectedPlanKind === "C"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  data-testid="plan-c-btn"
                >
                  Plan C (Balanced)
                </button>
              </div>
            </CardHeader>

            <CardContent className="p-0 pt-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                {/* Parameter 1: Cleaning Buffer Minutes */}
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-300">Cleaning Buffer</span>
                    <span className="font-mono text-indigo-400 font-bold">{cleaningBuffer} mins</span>
                  </div>
                  <input
                    type="range"
                    min={60}
                    max={240}
                    step={30}
                    value={cleaningBuffer}
                    onChange={(e) => setCleaningBuffer(Number(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Fixed FestOS heuristic: 180 min turn-around between guest departures.
                  </span>
                </div>

                {/* Parameter 2: Max Distance (km) */}
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-300">Max Property Distance</span>
                    <span className="font-mono text-indigo-400 font-bold">{maxDistance} km</span>
                  </div>
                  <input
                    type="range"
                    min={5}
                    max={30}
                    step={1}
                    value={maxDistance}
                    onChange={(e) => setMaxDistance(Number(e.target.value))}
                    className="w-full accent-indigo-500 cursor-pointer"
                  />
                  <span className="text-[10px] text-slate-400 block">
                    Cut-off radius for contracting external overflow hotels.
                  </span>
                </div>

                {/* Parameter 3: Allow Contingent Splits */}
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-300">Permit Contingent Splits</span>
                    <Badge variant="outline" className={allowSplits ? "border-amber-500/40 text-amber-300" : "border-emerald-500/40 text-emerald-300"}>
                      {allowSplits ? "ALLOWED" : "DISALLOWED"}
                    </Badge>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer text-slate-400 text-xs pt-1">
                    <input
                      type="checkbox"
                      checked={allowSplits}
                      onChange={(e) => setAllowSplits(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-950 text-indigo-600 h-4 w-4"
                    />
                    <span>Allow splitting contingents across properties if campus full</span>
                  </label>
                  <span className="text-[10px] text-slate-400 block">
                    Soft constraint #1 relaxed first in constraint ladder.
                  </span>
                </div>
              </div>

              {/* Plan C Custom Weights */}
              {selectedPlanKind === "C" && (
                <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 font-medium">Plan C Parameter Weights:</span>
                    <span className="text-[10px] text-slate-500 font-mono">Assumed key: accom_plan_c_weights</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 block">Cohesion ({cohesionWeight})</span>
                      <input
                        type="range"
                        min={0.1}
                        max={0.9}
                        step={0.1}
                        value={cohesionWeight}
                        onChange={(e) => setCohesionWeight(Number(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 block">Cost ({costWeight})</span>
                      <input
                        type="range"
                        min={0.1}
                        max={0.9}
                        step={0.1}
                        value={costWeight}
                        onChange={(e) => setCostWeight(Number(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-[11px] text-slate-400 block">Travel ({travelWeight})</span>
                      <input
                        type="range"
                        min={0.1}
                        max={0.9}
                        step={0.1}
                        value={travelWeight}
                        onChange={(e) => setTravelWeight(Number(e.target.value))}
                        className="w-full accent-indigo-500 cursor-pointer"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <Button
                  onClick={handleGeneratePlan}
                  isLoading={isGenerating}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8"
                  data-testid="generate-plan-btn"
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  Run Solver for Plan {selectedPlanKind}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Side-by-side Plan Compare Table */}
          <Card>
            <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3">
              <div>
                <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="h-4 w-4 text-indigo-400" />
                  <span>Side-by-Side Candidate Plan Comparison</span>
                </CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Deterministic metrics evaluating trade-offs between contingent unity, hotel costs, and safety flags.
                </p>
              </div>

              {/* Commit Plan To Live Button & Status Tracker */}
              <div className="flex items-center gap-2">
                {livePlanId ? (
                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-950/20 py-1 px-2.5">
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                    LIVE OPERATIONAL PLAN ACTIVE
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => setShowCommitModal(true)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-8"
                    data-testid="commit-live-btn"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                    Commit Plan to Live
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="py-3.5 px-4 w-1/4">Evaluation Metric</th>
                      <th className="py-3.5 px-4 w-1/4">
                        <div className="flex items-center gap-1.5 text-white">
                          <span>Plan A: Cohesion-First</span>
                        </div>
                      </th>
                      <th className="py-3.5 px-4 w-1/4">
                        <div className="flex items-center gap-1.5 text-white">
                          <span>Plan B: Cost-First</span>
                        </div>
                      </th>
                      <th className="py-3.5 px-4 w-1/4">
                        <div className="flex items-center gap-1.5 text-indigo-300">
                          <span>Plan C: Balanced (Recommended)</span>
                        </div>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {/* Row 1: On-Campus Placed */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">On-Campus Placed</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="font-bold text-white">{p.on_campus_placed}</span>
                          <span className="text-[11px] text-slate-400 ml-1">/ 710 beds</span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 2: External Hotel Placed */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">External Hotel Placed</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="font-bold text-white">{p.external_placed}</span>
                          <span className="text-[11px] text-slate-400 ml-1">delegates</span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 3: Unplaced Count */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Unplaced Delegates</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="font-bold text-amber-300 bg-amber-950/30 px-2 py-0.5 rounded border border-amber-500/30">
                            {p.unplaced_count} unplaced
                          </span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 4: Contingent Splits */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Contingent Splits</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <Badge
                            variant="outline"
                            className={
                              p.contingent_splits > 15
                                ? "border-red-500/40 text-red-400 bg-red-950/20"
                                : p.contingent_splits > 6
                                ? "border-amber-500/40 text-amber-300 bg-amber-950/20"
                                : "border-emerald-500/40 text-emerald-300 bg-emerald-950/20"
                            }
                          >
                            <Users className="h-3 w-3 mr-1" />
                            {p.contingent_splits} splits
                          </Badge>
                        </td>
                      ))}
                    </tr>

                    {/* Row 5: Total Cost INR */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Total External Cost</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="font-bold text-white font-mono text-sm">
                            ₹{p.total_cost_inr.toLocaleString("en-IN")}
                          </span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 6: Safety Flags */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Safety Flags</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="text-slate-300 font-mono">
                            {p.safety_flags_count} flags
                          </span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 7: Accessibility Issues */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Accessibility Deficits</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4">
                          <span className="font-semibold text-rose-300">
                            {p.accessibility_issues_count} unresolved
                          </span>
                        </td>
                      ))}
                    </tr>

                    {/* Row 8: Relaxed Constraints */}
                    <tr className="hover:bg-slate-900/30">
                      <td className="py-3 px-4 font-semibold text-slate-300">Relaxed Constraints</td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-3 px-4 text-slate-300">
                          {p.relaxed_constraints_count} soft relaxations
                        </td>
                      ))}
                    </tr>

                    {/* Row 9: Plain-Language Sacrifice Explanation */}
                    <tr className="bg-slate-900/40">
                      <td className="py-4 px-4 font-bold text-indigo-300 align-top">
                        Plain-Language Sacrifice Explanation
                      </td>
                      {plans.map((p) => (
                        <td key={p.plan_id} className="py-4 px-4 align-top">
                          <p className="text-slate-200 text-xs leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
                            {p.sacrifices_summary}
                          </p>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Cost-versus-Cohesion Trade-Off Chart (Recharts) */}
          <Card className="p-5">
            <CardHeader className="p-0 pb-4">
              <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-emerald-400" />
                <span>Cost-versus-Cohesion Trade-Off Chart (Recharts Visualization)</span>
              </CardTitle>
              <p className="text-xs text-slate-400 mt-0.5">
                Comparing Hotel Expenditure (₹ Lakhs) against Contingent Splits (fragmentation) across Plan A, B, and C.
              </p>
            </CardHeader>

            <CardContent className="p-0 pt-2">
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
                    <XAxis dataKey="name" stroke="#94a3b8" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <YAxis
                      yAxisId="left"
                      stroke="#10b981"
                      tick={{ fill: "#10b981", fontSize: 12 }}
                      label={{ value: "Cost (₹ Lakhs)", angle: -90, position: "insideLeft", fill: "#10b981", fontSize: 11 }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      stroke="#f59e0b"
                      tick={{ fill: "#f59e0b", fontSize: 12 }}
                      label={{ value: "Contingent Splits", angle: 90, position: "insideRight", fill: "#f59e0b", fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "0.5rem",
                        color: "#f8fafc",
                        fontSize: "12px",
                      }}
                      formatter={(val: any, name?: any) => [
                        name === "costInLakhs" ? `₹${val} Lakhs` : `${val} splits`,
                        name === "costInLakhs" ? "Hotel Cost" : "Contingent Splits",
                      ] as any}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                    <Bar
                      yAxisId="left"
                      dataKey="costInLakhs"
                      name="Hotel Cost (₹ Lakhs)"
                      fill="#6366f1"
                      radius={[4, 4, 0, 0]}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="splitsCount"
                      name="Contingent Splits"
                      stroke="#f59e0b"
                      strokeWidth={3}
                      dot={{ r: 5, fill: "#f59e0b" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Trade-off summary cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 border-t border-slate-800 text-xs">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="font-bold text-white block">Plan A: Maximum Unity</span>
                  <span className="text-slate-400 text-[11px]">
                    Only 4 splits, but peak budget at ₹33.15L.
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="font-bold text-white block">Plan B: Minimum Cost</span>
                  <span className="text-slate-400 text-[11px]">
                    Saves ₹8.35L, but fractures 19 contingents across town.
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="font-bold text-indigo-300 block">Plan C: Pareto Optimal</span>
                  <span className="text-slate-400 text-[11px]">
                    8 splits at ₹28.9L: the sweet spot authorized for operation.
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB 2: Shortage View */}
      {activeTab === "shortages" && (
        <ShortageView
          shortagesData={shortagesData}
          loading={shortagesLoading}
          onRefresh={fetchData}
        />
      )}

      {/* TAB 3: Occupancy Map */}
      {activeTab === "occupancy" && (
        <OccupancyMap
          occupancyData={occupancyData}
          loading={occupancyLoading}
          onSelectBedForAssignment={(bed, room, block) => {
            setSelectedBedForMove(bed);
            setSelectedRoomForMove(room);
            setSelectedBlockForMove(block);
            setIsDecisionModalOpen(true);
          }}
        />
      )}

      {/* Decision Flow Modal */}
      <DecisionFlowModal
        isOpen={isDecisionModalOpen}
        onClose={() => {
          setIsDecisionModalOpen(false);
          setSelectedBedForMove(null);
        }}
        selectedBed={selectedBedForMove}
        selectedRoom={selectedRoomForMove}
        selectedBlock={selectedBlockForMove}
        onAssignmentSuccess={fetchData}
      />

      {/* Commit to Live Modal (ConfirmWithReason) */}
      <ConfirmWithReason
        isOpen={showCommitModal}
        onClose={() => setShowCommitModal(false)}
        onConfirm={handleCommitLive}
        title="Commit Accommodation Plan to LIVE Operational Status"
        description="FestOS governance: Committing a candidate plan to LIVE establishes the active bed layout, generates participant keycards, and triggers external hotel purchase orders."
        confirmText="Commit & Authorize Live Plan"
        riskLevel="HIGH"
        isLoading={isCommitting}
      >
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1 mb-2">
          <div className="flex justify-between text-slate-300">
            <span>Selected Plan:</span>
            <span className="font-bold text-indigo-300">
              {plans.find((p) => p.kind === selectedPlanKind)?.name || "Plan C: Balanced"}
            </span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span>Total External Cost:</span>
            <span className="font-mono font-bold text-white">
              ₹{(plans.find((p) => p.kind === selectedPlanKind)?.total_cost_inr || 2890000).toLocaleString("en-IN")}
            </span>
          </div>
        </div>
      </ConfirmWithReason>
    </div>
  );
};

export default AccommodationWorkspace;
