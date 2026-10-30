import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  GitFork,
  AlertTriangle,
  Play,
  CheckCircle2,
  Trash2,
  Layers,
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
  SimulationScenario,
  ScenarioDisruptionOption,
} from "./types";
import { api } from "../../api/client";

export const ScenarioSimulatorWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("scen_live_fork_01");
  const [isForkModalOpen, setIsForkModalOpen] = useState(false);
  const [newForkName, setNewForkName] = useState("");
  const [newForkDescription, setNewForkDescription] = useState("");
  const [isApplyDisruptionModalOpen, setIsApplyDisruptionModalOpen] = useState(false);
  const [selectedDisruptionId, setSelectedDisruptionId] = useState("hostel_closure");
  const [isCommitModalOpen, setIsCommitModalOpen] = useState(false);
  const [commitReason, setCommitReason] = useState("");
  const [isScenariosDrawerOpen, setIsScenariosDrawerOpen] = useState(false);

  // 1. Fetch Scenarios List
  const { data: scenariosData, isLoading } = useQuery<{
    data: { items: SimulationScenario[]; catalog: ScenarioDisruptionOption[]; total: number };
  }>({
    queryKey: ["scenarios", "list"],
    queryFn: async () => {
      return api.get("/api/v1/scenarios");
    },
  });

  const scenarios: SimulationScenario[] = (scenariosData as any)?.items || (scenariosData as any)?.data?.items || [];
  const catalog: ScenarioDisruptionOption[] = (scenariosData as any)?.catalog || (scenariosData as any)?.data?.catalog || [];

  const currentScenario =
    scenarios.find((s) => s.id === selectedScenarioId) || scenarios[0];

  // 2. Fork Scenario Mutation
  const forkMutation = useMutation({
    mutationFn: async ({ name, description }: { name: string; description: string }) => {
      return api.post("/api/v1/scenarios", { name, description });
    },
    onSuccess: (res: any) => {
      addToast({
        type: "success",
        title: "Sandbox Created",
        message: "Live production state forked into isolated simulation environment.",
      });
      queryClient.invalidateQueries({ queryKey: ["scenarios", "list"] });
      setIsForkModalOpen(false);
      setNewForkName("");
      setNewForkDescription("");
      if (res?.data?.id) {
        setSelectedScenarioId(res.data.id);
      }
    },
  });

  // 3. Apply Disruption Mutation
  const applyDisruptionMutation = useMutation({
    mutationFn: async ({ scenarioId, disruptionId }: { scenarioId: string; disruptionId: string }) => {
      return api.post(`/api/v1/scenarios/${scenarioId}/simulate-incident`, {
        incident_type: disruptionId,
        target_id: "HOSTEL-03",
        severity: 4,
        details: "Injected stress test disruption into scenario sandbox.",
      });
    },
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Disruption Injected",
        message: "Impact computed and candidate recovery plans generated in sandbox.",
      });
      queryClient.invalidateQueries({ queryKey: ["scenarios", "list"] });
      setIsApplyDisruptionModalOpen(false);
    },
  });

  // 4. Commit Scenario Mutation
  const commitMutation = useMutation({
    mutationFn: async ({ scenarioId, reason }: { scenarioId: string; reason: string }) => {
      return api.post(`/api/v1/scenarios/${scenarioId}/commit`, { reason });
    },
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Scenario Changes Committed",
        message: "Approved recovery plan replayed through ChangeService onto live database.",
      });
      queryClient.invalidateQueries({ queryKey: ["scenarios", "list"] });
      setIsCommitModalOpen(false);
      setCommitReason("");
    },
  });

  // 5. Discard Scenario Mutation
  const discardMutation = useMutation({
    mutationFn: async (scenarioId: string) => {
      return api.post(`/api/v1/scenarios/${scenarioId}/discard`, {});
    },
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Scenario Discarded",
        message: "Simulation sandbox destroyed. Production database remains pristine.",
      });
      queryClient.invalidateQueries({ queryKey: ["scenarios", "list"] });
    },
  });

  const handleForkSubmit = () => {
    if (!newForkName.trim()) return;
    forkMutation.mutate({
      name: newForkName.trim(),
      description: newForkDescription.trim(),
    });
  };

  const handleApplyDisruption = () => {
    if (!currentScenario) return;
    applyDisruptionMutation.mutate({
      scenarioId: currentScenario.id,
      disruptionId: selectedDisruptionId,
    });
  };

  const handleCommitSubmit = () => {
    if (!currentScenario || !commitReason.trim()) return;
    commitMutation.mutate({
      scenarioId: currentScenario.id,
      reason: commitReason.trim(),
    });
  };

  return (
    <div className="space-y-6" data-testid="scenario-simulator-workspace">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Scenario Simulator</h1>
            <Badge variant="solid" status="PENDING">
              SANDBOX MODE
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Fork production state, simulate disruptions, compare candidate recovery plans, and commit or discard without touching live data.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            data-testid="parallel-scenarios-btn"
            variant="outline"
            size="sm"
            onClick={() => setIsScenariosDrawerOpen(true)}
          >
            <Layers className="w-3.5 h-3.5 mr-1" />
            Scenarios ({scenarios.length})
          </Button>

          <Button
            data-testid="fork-live-btn"
            variant="primary"
            size="sm"
            onClick={() => setIsForkModalOpen(true)}
          >
            <GitFork className="w-3.5 h-3.5 mr-1" />
            Fork Live Database
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-slate-400">Loading scenario simulations...</div>
      ) : !currentScenario ? (
        <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-400">
          No simulation scenarios found. Click "Fork Live Database" to create one.
        </div>
      ) : (
        <>
          {/* Stale Fork Alert Banner */}
          {currentScenario.isStale && (
            <div
              data-testid="stale-fork-warning"
              className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-4 flex items-start gap-3"
            >
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <div className="font-bold text-amber-200">
                  Stale Fork Warning: Live Database Has Mutated Since Fork Creation
                </div>
                <div className="text-amber-300/80 leading-relaxed">
                  Live state has recorded {currentScenario.liveMutationsSinceFork} mutations since this sandbox was forked (last synced: {currentScenario.lastSyncedAt}). Re-run or re-base recommended before committing any plan.
                </div>
              </div>
            </div>
          )}

          {/* Active Scenario Card & Controls */}
          <Card className="border-slate-800 bg-slate-900/90">
            <CardHeader className="pb-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg text-white" data-testid="current-scenario-name">
                      {currentScenario.name}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      status={
                        currentScenario.status === "COMMITTED"
                          ? "SUCCESS"
                          : currentScenario.status === "DISCARDED"
                          ? "REJECTED"
                          : "PENDING"
                      }
                    >
                      {currentScenario.status}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs text-slate-400 mt-1">
                    {currentScenario.description || "Isolated sandbox environment"} · Created by{" "}
                    {currentScenario.actorName}
                  </CardDescription>
                </div>

                {/* Scenario Control Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    data-testid="apply-disruption-btn"
                    variant="outline"
                    size="sm"
                    disabled={currentScenario.status !== "ACTIVE"}
                    onClick={() => setIsApplyDisruptionModalOpen(true)}
                  >
                    <Play className="w-3.5 h-3.5 mr-1 text-amber-400" />
                    Inject Disruption
                  </Button>

                  <Button
                    data-testid="commit-scenario-btn"
                    variant="primary"
                    size="sm"
                    disabled={currentScenario.status !== "ACTIVE"}
                    onClick={() => setIsCommitModalOpen(true)}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                    Commit (Approval)
                  </Button>

                  <Button
                    data-testid="discard-scenario-btn"
                    variant="outline"
                    size="sm"
                    disabled={currentScenario.status !== "ACTIVE"}
                    onClick={() => discardMutation.mutate(currentScenario.id)}
                    className="text-rose-400 hover:text-rose-300 hover:border-rose-800"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1" />
                    Discard
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Disruptions Injected in this sandbox */}
              <div className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/60 text-xs">
                <span className="font-semibold text-slate-300">Disruptions Injected in Sandbox: </span>
                {currentScenario.disruptionsApplied.length === 0 ? (
                  <span className="text-slate-500">None yet. Click "Inject Disruption" to simulate a catalog failure.</span>
                ) : (
                  <div className="mt-2 space-y-1.5">
                    {currentScenario.disruptionsApplied.map((da) => (
                      <div key={da.id} className="flex items-center justify-between text-slate-300 bg-slate-900/60 p-2 rounded">
                        <span className="font-medium">{da.summary}</span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Target: {da.targetId}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Side-by-Side Metric Comparison Against Live */}
              <div className="space-y-3" data-testid="metrics-comparison-table">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Side-by-Side Metric Comparison: Live Production vs. Sandbox
                </h3>

                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-slate-800/80 text-slate-400 font-medium">
                      <tr>
                        <th className="p-3">Metric Name</th>
                        <th className="p-3 text-right">Live Production</th>
                        <th className="p-3 text-right">Scenario Sandbox</th>
                        <th className="p-3 text-right">Delta</th>
                        <th className="p-3 text-center">Impact Evaluation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-900/60 font-mono">
                      {currentScenario.metricsComparison.map((m) => (
                        <tr key={m.key} className="hover:bg-slate-800/40">
                          <td className="p-3 font-sans font-medium text-white">{m.label}</td>
                          <td className="p-3 text-right text-slate-300">
                            {m.liveValue} {m.unit || ""}
                          </td>
                          <td className="p-3 text-right font-bold text-white">
                            {m.scenarioValue} {m.unit || ""}
                          </td>
                          <td
                            className={`p-3 text-right font-bold ${
                              m.impactStatus === "IMPROVED"
                                ? "text-emerald-400"
                                : m.impactStatus === "DEGRADED"
                                ? "text-rose-400"
                                : "text-slate-400"
                            }`}
                          >
                            {m.delta}
                          </td>
                          <td className="p-3 text-center font-sans">
                            <Badge
                              variant="outline"
                              status={
                                m.impactStatus === "IMPROVED"
                                  ? "SUCCESS"
                                  : m.impactStatus === "DEGRADED"
                                  ? "REJECTED"
                                  : "PENDING"
                              }
                            >
                              {m.impactStatus}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Candidate Recovery Plans in Sandbox */}
              {currentScenario.candidatePlans.length > 0 && (
                <div className="space-y-3" data-testid="candidate-plans-section">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Candidate Recovery Plans Evaluated by Logic Engine
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {currentScenario.candidatePlans.map((plan) => (
                      <div
                        key={plan.id}
                        data-testid={`plan-card-${plan.id}`}
                        className={`p-4 rounded-xl border text-xs space-y-3 transition-all ${
                          plan.isRecommended
                            ? "border-emerald-500/60 bg-emerald-950/20"
                            : "border-slate-800 bg-slate-900/70"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="font-bold text-white text-sm">{plan.name}</div>
                          {plan.isRecommended && (
                            <Badge variant="solid" status="SUCCESS">
                              RECOMMENDED
                            </Badge>
                          )}
                        </div>

                        <p className="text-slate-400 leading-relaxed">{plan.strategy}</p>

                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-center font-mono">
                          <div className="p-2 rounded bg-slate-800/50">
                            <div className="text-[10px] text-slate-500 font-sans">People Moved</div>
                            <div className="text-sm font-bold text-white">{plan.peopleMoved}</div>
                          </div>
                          <div className="p-2 rounded bg-slate-800/50">
                            <div className="text-[10px] text-slate-500 font-sans">Schedule Delay</div>
                            <div className="text-sm font-bold text-white">{plan.scheduleChanges}h</div>
                          </div>
                          <div className="p-2 rounded bg-slate-800/50">
                            <div className="text-[10px] text-slate-500 font-sans">Cost Delta</div>
                            <div className="text-sm font-bold text-emerald-400">
                              ₹{plan.costDeltaInr.toLocaleString()}
                            </div>
                          </div>
                        </div>

                        {plan.constraintsRelaxed.length > 0 && (
                          <div className="text-[11px] text-amber-300/90 pt-1">
                            Relaxed Constraints: {plan.constraintsRelaxed.join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Fork Modal */}
      {isForkModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setIsForkModalOpen(false)}
          title="Fork Live Database into Simulation Sandbox"
          size="md"
        >
          <div className="space-y-4" data-testid="fork-modal">
            <div className="text-xs text-slate-400 leading-relaxed">
              Creates a point-in-time snapshot of all canonical tables (participants, rooms, shifts, vendors). No mutations executed inside the sandbox will affect production state.
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Scenario Name <span className="text-rose-400">*</span>
              </label>
              <input
                data-testid="fork-name-input"
                type="text"
                placeholder="e.g. Day 2 Night Weather Crisis Simulation"
                value={newForkName}
                onChange={(e) => setNewForkName(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
              <textarea
                data-testid="fork-description-input"
                rows={2}
                placeholder="Goal and parameters of this test drill..."
                value={newForkDescription}
                onChange={(e) => setNewForkDescription(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setIsForkModalOpen(false)}>
                Cancel
              </Button>
              <Button
                data-testid="submit-fork-btn"
                variant="primary"
                size="sm"
                onClick={handleForkSubmit}
                disabled={!newForkName.trim()}
              >
                Create Fork
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Inject Disruption Modal */}
      {isApplyDisruptionModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setIsApplyDisruptionModalOpen(false)}
          title="Select Disruption from Catalog to Inject"
          size="md"
        >
          <div className="space-y-4" data-testid="inject-disruption-modal">
            <div className="space-y-2">
              {catalog.map((opt) => (
                <div
                  key={opt.id}
                  data-testid={`catalog-option-${opt.id}`}
                  onClick={() => setSelectedDisruptionId(opt.id)}
                  className={`p-3 rounded-lg border cursor-pointer text-xs space-y-1 transition-all ${
                    selectedDisruptionId === opt.id
                      ? "border-indigo-500 bg-indigo-950/40"
                      : "border-slate-800 bg-slate-900/60 hover:bg-slate-800/40"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">{opt.name}</span>
                    <Badge variant="outline">{opt.severity}</Badge>
                  </div>
                  <p className="text-slate-400">{opt.description}</p>
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setIsApplyDisruptionModalOpen(false)}>
                Cancel
              </Button>
              <Button
                data-testid="submit-disruption-btn"
                variant="primary"
                size="sm"
                onClick={handleApplyDisruption}
              >
                Inject into Sandbox
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Commit Approval Modal */}
      {isCommitModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setIsCommitModalOpen(false)}
          title="Authorize & Commit Sandbox Plan to Live Production"
          size="md"
        >
          <div className="space-y-4" data-testid="commit-modal">
            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-500/40 text-xs text-amber-200">
              Committing will replay the approved candidate plan across production tables through ChangeService.
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Mandatory Approval Justification <span className="text-rose-400">*</span>
              </label>
              <textarea
                data-testid="commit-reason-input"
                rows={3}
                placeholder="Under FestOS principles, record operational justification for committing this plan..."
                value={commitReason}
                onChange={(e) => setCommitReason(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setIsCommitModalOpen(false)}>
                Cancel
              </Button>
              <Button
                data-testid="confirm-commit-btn"
                variant="primary"
                size="sm"
                onClick={handleCommitSubmit}
                disabled={!commitReason.trim()}
              >
                Authorize & Commit
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Parallel Scenarios Drawer */}
      {isScenariosDrawerOpen && (
        <Drawer
          isOpen={true}
          onClose={() => setIsScenariosDrawerOpen(false)}
          title={`Simulation Scenarios (${scenarios.length})`}
          width="max-w-md"
        >
          <div className="space-y-3" data-testid="scenarios-drawer">
            {scenarios.map((scen) => (
              <div
                key={scen.id}
                data-testid={`scenario-list-item-${scen.id}`}
                onClick={() => {
                  setSelectedScenarioId(scen.id);
                  setIsScenariosDrawerOpen(false);
                }}
                className={`p-3 rounded-lg border cursor-pointer text-xs space-y-1.5 transition-all ${
                  scen.id === currentScenario.id
                    ? "border-indigo-500 bg-indigo-950/30"
                    : "border-slate-800 bg-slate-900/60 hover:bg-slate-800/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">{scen.name}</span>
                  <Badge variant="outline">{scen.status}</Badge>
                </div>
                <div className="text-slate-400 truncate">{scen.description}</div>
                <div className="text-[11px] text-slate-500 flex items-center justify-between pt-1">
                  <span>{scen.actorName}</span>
                  {scen.isStale && <span className="text-amber-400 font-bold">Stale Fork</span>}
                </div>
              </div>
            ))}
          </div>
        </Drawer>
      )}
    </div>
  );
};

export default ScenarioSimulatorWorkspace;
