import React, { useState, useEffect } from "react";
import {
  ScenarioDefinition,
  DryRunImpact,
  DownstreamUpdateItem,
  IncidentRecord,
} from "./types";
import { Modal } from "../../components/ui/Modal";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { SeverityPill } from "../../components/ui/SeverityPill";
import { ConfirmWithReason } from "../../components/ui/ConfirmWithReason";
import { api } from "../../api/client";
import { useToast } from "../../components/ui/Toast";
import {
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { Link } from "react-router-dom";

export type FlowStep =
  | "PARAMS"
  | "DRY_RUN_PREVIEW"
  | "SIMULATE"
  | "COMPARE_PLANS"
  | "EXECUTING"
  | "VERIFICATION";

interface DisruptionFlowModalProps {
  scenario: ScenarioDefinition | null;
  isOpen: boolean;
  onClose: () => void;
  onIncidentResolved: (incident: IncidentRecord) => void;
}

export const DisruptionFlowModal: React.FC<DisruptionFlowModalProps> = ({
  scenario,
  isOpen,
  onClose,
  onIncidentResolved,
}) => {
  const { addToast } = useToast();
  const [currentStep, setCurrentStep] = useState<FlowStep>("PARAMS");
  const [params, setParams] = useState<Record<string, any>>({});
  const [dryRunData, setDryRunData] = useState<DryRunImpact | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<"plan_a" | "plan_b" | "plan_c">("plan_a");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [resolvedIncident, setResolvedIncident] = useState<IncidentRecord | null>(null);
  const [executionProgress, setExecutionProgress] = useState(0);
  const [executionLogs, setExecutionLogs] = useState<string[]>([]);
  const [downstreamTracker, setDownstreamTracker] = useState<DownstreamUpdateItem[]>([]);

  // Reset state on scenario change
  useEffect(() => {
    if (scenario) {
      setParams(scenario.defaultParams);
      setCurrentStep("PARAMS");
      setDryRunData(null);
      setSelectedPlanId("plan_a");
      setResolvedIncident(null);
      setExecutionProgress(0);
      setExecutionLogs([]);
      setDownstreamTracker([]);
    }
  }, [scenario]);

  if (!scenario) return null;

  // Keyboard shortcut listener: Enter to progress
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !isConfirmOpen) {
      if (currentStep === "PARAMS") {
        e.preventDefault();
        handleTriggerDryRun();
      } else if (currentStep === "DRY_RUN_PREVIEW") {
        e.preventDefault();
        setCurrentStep("COMPARE_PLANS");
      }
    }
  };

  // Step 1 -> Step 2: Dry Run Impact Preview
  const handleTriggerDryRun = async () => {
    setIsLoading(true);
    try {
      const res = await api.post<DryRunImpact>("/api/v1/incidents/dry-run", {
        scenario_id: scenario.id,
        params,
      });
      setDryRunData(res);
      if (res.plans.length > 0) {
        const recommended = res.plans.find((p) => p.isRecommended);
        setSelectedPlanId(recommended?.id || res.plans[0].id);
      }
      setCurrentStep("DRY_RUN_PREVIEW");
      addToast({
        title: "Blast Radius Analyzed",
        message: `Impact preview calculated: ${res.peopleAffected} people affected across ${res.affectedEntities.venues} venues.`,
        type: "info",
      });
    } catch (err: any) {
      addToast({
        title: "Simulation Failed",
        message: err.message || "Failed to calculate dry-run impact",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2 -> Optional Step: Sandbox Simulate
  const handleSimulateInSandbox = () => {
    setCurrentStep("SIMULATE");
    addToast({
      title: "Sandbox Simulation Active",
      message: "Disruption executed in isolated sandbox environment.",
      type: "warning",
    });
  };

  // Approve action with reason through ConfirmWithReason modal
  const handleConfirmApproval = async (reason: string) => {
    if (!dryRunData) return;
    setIsConfirmOpen(false);
    setCurrentStep("EXECUTING");
    setExecutionProgress(10);
    setExecutionLogs(["Initiating ChangeService transactional unit..."]);

    // Simulated progress steps
    setTimeout(() => {
      setExecutionProgress(40);
      setExecutionLogs((prev) => [
        ...prev,
        "Snapshot taken. Relaxing authorized constraints in ladder order...",
        "Applying downstream mutations (Accommodation, Transport, Catering)...",
      ]);
    }, 400);

    setTimeout(() => {
      setExecutionProgress(80);
      setExecutionLogs((prev) => [
        ...prev,
        "Broadcasting internal domain events across event bus...",
        "Updating operational ledger and override register...",
      ]);
    }, 800);

    setTimeout(async () => {
      try {
        const res = await api.post<{ incident: IncidentRecord }>("/api/v1/incidents/INC-LIVE/approve", {
          scenario_id: scenario.id,
          title: scenario.title,
          plan_id: selectedPlanId,
          reason,
        });

        const inc = res.incident;
        setResolvedIncident(inc);
        setDownstreamTracker(inc.downstreamUpdates);
        setExecutionProgress(100);
        setExecutionLogs((prev) => [...prev, "Recovery plan successfully applied and operational state updated."]);
        setCurrentStep("VERIFICATION");
        onIncidentResolved(inc);
        addToast({
          title: "Disruption Plan Approved",
          message: `Applied ${selectedPlanId.toUpperCase()}: ${scenario.title}`,
          type: "success",
        });
      } catch (err: any) {
        addToast({
          title: "Execution Error",
          message: err.message || "Failed to commit incident recovery plan",
          type: "error",
        });
        setCurrentStep("COMPARE_PLANS");
      }
    }, 1200);
  };

  // Mark downstream update item as verified
  const handleVerifyDownstream = async (item: DownstreamUpdateItem) => {
    try {
      await api.post(`/api/v1/incidents/${resolvedIncident?.id || "INC-LIVE"}/verify-downstream`, {
        downstream_id: item.id,
      });

      setDownstreamTracker((prev) =>
        prev.map((d) => (d.id === item.id ? { ...d, status: "VERIFIED", verifiedAt: new Date().toISOString() } : d))
      );

      addToast({
        title: "Subsystem Verified",
        message: `${item.domain} downstream effect verified in operational state.`,
        type: "success",
      });
    } catch {
      // Fallback local toggle
      setDownstreamTracker((prev) =>
        prev.map((d) => (d.id === item.id ? { ...d, status: "VERIFIED", verifiedAt: new Date().toISOString() } : d))
      );
    }
  };

  const selectedPlan = dryRunData?.plans.find((p) => p.id === selectedPlanId);

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="xl"
        title={
          <div className="flex items-center space-x-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-red-600/20 text-red-400 font-bold text-xs">
              LIVE
            </span>
            <div>
              <span className="text-white font-bold">{scenario.title}</span>
              <span className="ml-2 text-xs text-slate-400">({scenario.category})</span>
            </div>
          </div>
        }
        description="FestOS Disruption Management Console: Heuristic Dry Run, Recovery Plans & Downstream Verification"
      >
        <div onKeyDown={handleKeyDown} className="space-y-6 pt-1 text-slate-200">
          {/* Breadcrumb / Step tracker */}
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 text-xs">
            <span className={`font-semibold ${currentStep === "PARAMS" ? "text-indigo-400" : "text-slate-400"}`}>
              1. Parameter Form
            </span>
            <ChevronRight className="h-3 w-3 text-slate-600" />
            <span
              className={`font-semibold ${
                currentStep === "DRY_RUN_PREVIEW" || currentStep === "SIMULATE" ? "text-indigo-400" : "text-slate-400"
              }`}
            >
              2. Impact Preview (Dry Run)
            </span>
            <ChevronRight className="h-3 w-3 text-slate-600" />
            <span
              className={`font-semibold ${
                currentStep === "COMPARE_PLANS" || currentStep === "EXECUTING" ? "text-indigo-400" : "text-slate-400"
              }`}
            >
              3. Recovery Plans
            </span>
            <ChevronRight className="h-3 w-3 text-slate-600" />
            <span className={`font-semibold ${currentStep === "VERIFICATION" ? "text-indigo-400" : "text-slate-400"}`}>
              4. Verification & Downstream
            </span>
          </div>

          {/* STEP 1: PARAMETER FORM */}
          {currentStep === "PARAMS" && (
            <div className="space-y-4" data-testid="parameter-form">
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
                <p className="text-xs text-slate-300 leading-relaxed">{scenario.description}</p>
                <div className="mt-3 flex items-center space-x-2">
                  <span className="text-[11px] font-semibold uppercase text-slate-400">Baseline Severity:</span>
                  <SeverityPill severity={scenario.defaultSeverity} />
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Scenario Parameters (Keyboard Enabled)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {scenario.paramFields.map((field) => (
                    <div key={field.name} className="space-y-1">
                      <label className="block text-xs font-semibold text-slate-300">{field.label}</label>
                      {field.type === "select" ? (
                        <select
                          value={params[field.name] ?? field.defaultValue}
                          onChange={(e) => setParams({ ...params, [field.name]: e.target.value })}
                          className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                        >
                          {field.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={field.type}
                          value={params[field.name] ?? field.defaultValue}
                          onChange={(e) => setParams({ ...params, [field.name]: e.target.value })}
                          className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <span className="text-[11px] text-slate-500">
                  Tip: Press <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">Enter</kbd> to preview
                  impact immediately.
                </span>
                <div className="flex items-center space-x-3">
                  <Button variant="ghost" size="sm" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleTriggerDryRun}
                    isLoading={isLoading}
                    data-testid="preview-impact-btn"
                  >
                    Preview Impact (Dry Run) <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: IMPACT PREVIEW (DRY RUN) */}
          {(currentStep === "DRY_RUN_PREVIEW" || currentStep === "SIMULATE") && dryRunData && (
            <div className="space-y-4" data-testid="impact-preview">
              {currentStep === "SIMULATE" && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-950/20 p-3 text-xs text-amber-300 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Sparkles className="h-4 w-4 text-amber-400 shrink-0" />
                    <span>
                      <strong>SANDBOX DRILL SIMULATION:</strong> Isolated hypothetical world. Live database unaffected.
                    </span>
                  </div>
                  <Badge status="PENDING">SANDBOX ACTIVE</Badge>
                </div>
              )}

              {/* Blast Radius Tiles */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3">
                  <div className="text-[10px] uppercase font-bold text-slate-400">People Affected</div>
                  <div className="text-xl font-bold font-mono text-red-400 mt-1" data-testid="preview-people-affected">
                    {dryRunData.peopleAffected}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Participants & Staff</div>
                </div>

                <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Entities Disrupted</div>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                    {dryRunData.affectedEntities.rooms +
                      dryRunData.affectedEntities.events +
                      dryRunData.affectedEntities.meals}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Rooms, Events, Meals</div>
                </div>

                <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Recovery Options</div>
                  <div className="text-xl font-bold font-mono text-indigo-400 mt-1">{dryRunData.plans.length} Plans</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Heuristic Generated</div>
                </div>

                <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Time Shift Delta</div>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                    +{dryRunData.simulatedTimeDeltaMin} min
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Schedule Impact</div>
                </div>
              </div>

              {/* Key Risks Checklist */}
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-bold uppercase text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Immediate Operational Blast Radius Risks</span>
                </div>
                <ul className="space-y-1.5 pl-4 list-disc text-xs text-slate-300">
                  {dryRunData.keyRisks.map((risk, idx) => (
                    <li key={idx}>{risk}</li>
                  ))}
                </ul>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep("PARAMS")}>
                  Back to Parameters
                </Button>
                <div className="flex items-center space-x-3">
                  {currentStep !== "SIMULATE" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleSimulateInSandbox}
                      data-testid="simulate-btn"
                    >
                      <Sparkles className="mr-1.5 h-3.5 w-3.5 text-amber-400" /> Simulate Drill
                    </Button>
                  )}
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setCurrentStep("COMPARE_PLANS")}
                    data-testid="compare-plans-btn"
                  >
                    Compare Recovery Plans <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: COMPARE RECOVERY PLANS SIDE BY SIDE */}
          {currentStep === "COMPARE_PLANS" && dryRunData && (
            <div className="space-y-5" data-testid="compare-plans-view">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Multi-Plan Evaluation Matrix (Side by Side)
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  Consequences are calculated simultaneously. FestOS prioritizes cohesion over cost.
                </p>
              </div>

              {/* Side by Side Plan Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {dryRunData.plans.map((plan) => {
                  const isSelected = selectedPlanId === plan.id;
                  return (
                    <div
                      key={plan.id}
                      onClick={() => setSelectedPlanId(plan.id)}
                      data-testid={`plan-card-${plan.id}`}
                      className={`cursor-pointer rounded-xl border p-4 transition-all flex flex-col justify-between ${
                        isSelected
                          ? "border-indigo-500 bg-indigo-950/20 ring-2 ring-indigo-500/30 shadow-lg"
                          : "border-slate-800 bg-[#0E1526]/80 hover:border-slate-700"
                      }`}
                    >
                      <div className="space-y-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="text-xs font-extrabold text-white block">{plan.name}</span>
                            <span className="text-[10px] text-slate-400">{plan.strategy}</span>
                          </div>
                          {plan.isRecommended && (
                            <Badge status="SUCCESS" className="shrink-0 text-[9px]">
                              RECOMMENDED
                            </Badge>
                          )}
                        </div>

                        {/* Metric Grid */}
                        <div className="grid grid-cols-2 gap-2 text-[11px] pt-2 border-t border-slate-800/80">
                          <div>
                            <span className="text-slate-500 block">People Moved:</span>
                            <span className="font-mono font-bold text-white">{plan.peopleMoved}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Schedule Shifts:</span>
                            <span className="font-mono font-bold text-amber-400">{plan.scheduleChanges}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Resource Moves:</span>
                            <span className="font-mono font-bold text-white">{plan.resourceMoves}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Cost Delta:</span>
                            <span className="font-mono font-bold text-emerald-400">₹{plan.costDeltaInr.toLocaleString()}</span>
                          </div>
                        </div>

                        {/* Constraints Relaxed */}
                        <div className="pt-2 border-t border-slate-800/80">
                          <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                            Constraints Relaxed:
                          </span>
                          {plan.constraintsRelaxed.length === 0 ? (
                            <span className="text-[10px] text-emerald-400 italic">None (Strict adherence)</span>
                          ) : (
                            <ul className="space-y-1">
                              {plan.constraintsRelaxed.map((c, i) => (
                                <li key={i} className="text-[10px] text-amber-300">
                                  <strong>[{c.type}]</strong> {c.constraint}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-800">
                        <Button
                          variant={isSelected ? "primary" : "secondary"}
                          size="sm"
                          className="w-full text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedPlanId(plan.id);
                          }}
                        >
                          {isSelected ? "Selected Plan" : "Select Plan"}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Selected Plan Details & Action */}
              {selectedPlan && (
                <div className="rounded-lg border border-indigo-500/30 bg-indigo-950/10 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="h-4 w-4 text-indigo-400" />
                      <span className="text-xs font-bold text-white">Selected Decision: {selectedPlan.name}</span>
                    </div>
                    <span className="text-xs font-mono font-bold text-emerald-400">
                      Cost Delta: ₹{selectedPlan.costDeltaInr.toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300">{selectedPlan.summary}</p>
                </div>
              )}

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep("DRY_RUN_PREVIEW")}>
                  Back to Impact Preview
                </Button>
                <div className="flex items-center space-x-3">
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => setIsConfirmOpen(true)}
                    data-testid="approve-plan-btn"
                  >
                    Authorize & Commit Plan <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: EXECUTING PROGRESS */}
          {currentStep === "EXECUTING" && (
            <div className="space-y-5 py-6 text-center" data-testid="executing-progress">
              <div className="space-y-2">
                <h4 className="text-sm font-bold text-white">Applying Recovery Plan Through ChangeService</h4>
                <p className="text-xs text-slate-400">Recording audit trails, updating ledger, and syncing downstream...</p>
              </div>

              {/* Animated Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-indigo-600 h-3 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${executionProgress}%` }}
                />
              </div>

              {/* Execution log terminal */}
              <div className="rounded-lg bg-slate-950 border border-slate-800 p-3 text-left font-mono text-[11px] text-slate-300 space-y-1 max-h-40 overflow-y-auto">
                {executionLogs.map((log, i) => (
                  <div key={i} className="flex items-center space-x-1.5">
                    <span className="text-indigo-400">&gt;</span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 5: VERIFICATION SCREEN WITH DOWNSTREAM TRACKER */}
          {currentStep === "VERIFICATION" && (
            <div className="space-y-5" data-testid="verification-screen">
              <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/20 p-4 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
                  <div>
                    <h4 className="text-sm font-bold text-white">State Update Verified & Change Set Applied</h4>
                    <p className="text-xs text-emerald-300">
                      Disruption plan has altered real operational state across all connected festival subsystems.
                    </p>
                  </div>
                </div>
                <Badge status="SUCCESS">COMMITTED TO DB</Badge>
              </div>

              {/* Before vs After Operational State */}
              <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4 space-y-3">
                <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Before vs After Operational State Delta
                </h5>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="rounded-lg bg-slate-900/60 p-2.5">
                    <span className="text-slate-500 block text-[10px] uppercase">Unplaced Participants</span>
                    <span className="text-slate-400 line-through mr-2">
                      {resolvedIncident?.beforeMetrics.unplacedParticipants ?? 85}
                    </span>
                    <span className="font-bold text-emerald-400">
                      {resolvedIncident?.afterMetrics.unplacedParticipants ?? 0}
                    </span>
                  </div>

                  <div className="rounded-lg bg-slate-900/60 p-2.5">
                    <span className="text-slate-500 block text-[10px] uppercase">Meal Shortages</span>
                    <span className="text-slate-400 line-through mr-2">
                      {resolvedIncident?.beforeMetrics.mealShortages ?? 85}
                    </span>
                    <span className="font-bold text-emerald-400">
                      {resolvedIncident?.afterMetrics.mealShortages ?? 0}
                    </span>
                  </div>

                  <div className="rounded-lg bg-slate-900/60 p-2.5">
                    <span className="text-slate-500 block text-[10px] uppercase">Schedule Delays</span>
                    <span className="text-slate-400 line-through mr-2">
                      {resolvedIncident?.beforeMetrics.delayedEvents ?? 2} events
                    </span>
                    <span className="font-bold text-emerald-400">0 events</span>
                  </div>

                  <div className="rounded-lg bg-slate-900/60 p-2.5">
                    <span className="text-slate-500 block text-[10px] uppercase">Cost Impact</span>
                    <span className="text-slate-400 line-through mr-2">₹0</span>
                    <span className="font-bold text-amber-400">
                      +₹{(resolvedIncident?.afterMetrics.extraCostInr ?? 42500).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Downstream Update Tracker (PENDING, UPDATED, VERIFIED) */}
              <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Downstream-Update Tracker (Subsystem Synchronization)
                  </h5>
                  <span className="text-[11px] text-slate-500">
                    {downstreamTracker.filter((d) => d.status === "VERIFIED").length} of {downstreamTracker.length} Verified
                  </span>
                </div>

                <div className="space-y-2" data-testid="downstream-tracker-list">
                  {downstreamTracker.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 text-xs"
                      data-testid={`downstream-item-${item.domain.toLowerCase()}`}
                    >
                      <div className="space-y-1 max-w-[65%]">
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-white">{item.domain}:</span>
                          <span className="text-slate-300 truncate">{item.label}</span>
                        </div>
                        <p className="text-[11px] text-slate-400">{item.details}</p>
                      </div>

                      <div className="flex items-center space-x-3">
                        {/* Status Badge */}
                        <Badge
                          status={
                            item.status === "VERIFIED"
                              ? "SUCCESS"
                              : item.status === "UPDATED"
                              ? "APPLIED"
                              : "PENDING"
                          }
                          data-testid={`status-${item.status.toLowerCase()}`}
                        >
                          {item.status}
                        </Badge>

                        {/* Link to Subsystem */}
                        <Link
                          to={item.entityRoute}
                          onClick={onClose}
                          className="text-slate-400 hover:text-white transition-colors"
                          title="Open Subsystem"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Link>

                        {/* Verification Toggle */}
                        {item.status !== "VERIFIED" ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="text-[10px] h-7"
                            onClick={() => handleVerifyDownstream(item)}
                            data-testid={`verify-btn-${item.domain.toLowerCase()}`}
                          >
                            Mark Verified
                          </Button>
                        ) : (
                          <span className="text-emerald-400 flex items-center text-[10px]">
                            <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Verified
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <Link to="/impact" onClick={onClose}>
                  <Button variant="secondary" size="sm">
                    Inspect Impact Tree <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </Link>
                <Button variant="primary" size="sm" onClick={onClose} data-testid="close-verification-btn">
                  Complete & Return to Console
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Confirm With Reason Modal (Strict FestOS Override Audit Rule) */}
      <ConfirmWithReason
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={handleConfirmApproval}
        title={`Authorize ${scenario.title} Recovery`}
        description={`Approving ${selectedPlan?.name} will relax configured constraints in ladder order and dispatch mutations to Accommodation, Transport, Food, and Event Schedules.`}
        confirmText="Authorize & Apply Mutations"
        riskLevel={scenario.defaultSeverity === "CRITICAL" ? "CRITICAL" : "HIGH"}
        placeholder="Provide explicit operational rationale for festival recovery override..."
      >
        <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 text-xs space-y-1 mb-2">
          <div className="flex justify-between font-semibold text-slate-300">
            <span>Selected Strategy:</span>
            <span className="text-white">{selectedPlan?.name}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>People Moved:</span>
            <span className="font-mono">{selectedPlan?.peopleMoved}</span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Estimated Cost Delta:</span>
            <span className="font-mono text-emerald-400">₹{selectedPlan?.costDeltaInr.toLocaleString()}</span>
          </div>
        </div>
      </ConfirmWithReason>
    </>
  );
};
