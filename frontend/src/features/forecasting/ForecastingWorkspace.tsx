import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  Edit3,
  Info,
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
  useToast,
} from "../../components/ui";
import {
  ForecastDataset,
  AssumptionItem,
} from "./types";
import { api } from "../../api/client";

export const ForecastingWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [editingAssumption, setEditingAssumption] = useState<AssumptionItem | null>(null);
  const [newAssumptionValue, setNewAssumptionValue] = useState<string | number>("");
  const [updateReason, setUpdateReason] = useState("");
  const [selectedDomain, setSelectedDomain] = useState<"all" | "accommodation" | "food" | "transport">("all");

  // 1. Fetch Forecast Datasets
  const { data: forecastData, isLoading: forecastLoading } = useQuery<{
    data: { datasets: ForecastDataset[] };
  }>({
    queryKey: ["forecasting", "datasets"],
    queryFn: async () => {
      return api.get("/api/v1/forecasting/datasets");
    },
  });

  // 2. Fetch Assumptions List
  const { data: assumptionsData } = useQuery<{
    data: { items: AssumptionItem[]; total: number };
  }>({
    queryKey: ["assumptions", "list"],
    queryFn: async () => {
      return api.get("/api/v1/assumptions");
    },
  });

  // Mutation to update assumption
  const updateAssumptionMutation = useMutation({
    mutationFn: async ({ key, value, reason }: { key: string; value: any; reason: string }) => {
      return api.patch(`/api/v1/assumptions/${key}`, { value, reason });
    },
    onSuccess: (_, variables) => {
      addToast({
        type: "success",
        title: "Assumption Updated",
        message: `Updated '${variables.key}' to ${variables.value}. Projections recalculated.`,
      });
      queryClient.invalidateQueries({ queryKey: ["assumptions", "list"] });
      queryClient.invalidateQueries({ queryKey: ["forecasting", "datasets"] });
      setEditingAssumption(null);
      setUpdateReason("");
    },
    onError: () => {
      addToast({
        type: "error",
        title: "Update Failed",
        message: "Failed to persist assumption value.",
      });
    },
  });

  const datasets: ForecastDataset[] = (forecastData as any)?.datasets || (forecastData as any)?.data?.datasets || [];
  const assumptions: AssumptionItem[] = (assumptionsData as any)?.items || (assumptionsData as any)?.data?.items || [];

  const filteredDatasets =
    selectedDomain === "all"
      ? datasets
      : datasets.filter((d) => d.domain === selectedDomain);

  const handleEditClick = (assumption: AssumptionItem) => {
    setEditingAssumption(assumption);
    setNewAssumptionValue(assumption.value);
    setUpdateReason("");
  };

  const handleSaveAssumption = () => {
    if (!editingAssumption) return;
    if (!updateReason.trim()) {
      addToast({
        type: "error",
        title: "Reason Required",
        message: "Under FestOS principles, changing an operational assumption requires a recorded reason.",
      });
      return;
    }
    updateAssumptionMutation.mutate({
      key: editingAssumption.key,
      value: Number(newAssumptionValue) || newAssumptionValue,
      reason: updateReason.trim(),
    });
  };

  return (
    <div className="space-y-6" data-testid="forecasting-workspace">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Demand & Capacity Forecasting</h1>
            <Badge variant="solid" status="SUCCESS">
              RECHARTS PROJECTION ENGINE
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Empirical ground truth vs heuristic projection curves. Compare verified demand against editable operational assumptions.
          </p>
        </div>

        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
          {(["all", "accommodation", "food", "transport"] as const).map((dom) => (
            <button
              key={dom}
              onClick={() => setSelectedDomain(dom)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors ${
                selectedDomain === dom
                  ? "bg-indigo-600 text-white font-bold"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {dom}
            </button>
          ))}
        </div>
      </div>

      {/* PROJECTION vs ASSUMPTION Visual Legend Banner */}
      <div
        className="rounded-xl border border-indigo-500/30 bg-slate-900/90 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
        data-testid="projection-vs-assumption-legend"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-950 text-indigo-400">
            <Info className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-white">
              Data Provenance Architecture: PROJECTION vs. ASSUMPTION
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Distinguishing empirical commitments from probabilistic heuristics.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs font-mono">
          <div className="flex items-center gap-2">
            <div className="w-5 h-0.5 bg-indigo-400" />
            <span className="text-indigo-300 font-bold">PROJECTION</span>
            <span className="text-slate-500 text-[11px] font-sans">(Solid · Verified Ground Truth)</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="w-5 h-0.5 border-t-2 border-dashed border-amber-400" />
            <span className="text-amber-300 font-bold">ASSUMPTION</span>
            <span className="text-slate-500 text-[11px] font-sans">(Dashed · Heuristic Model)</span>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      {forecastLoading ? (
        <div className="p-12 text-center text-slate-400">Computing demand forecasts...</div>
      ) : (
        <div className="space-y-6">
          {filteredDatasets.map((ds) => {
            const relatedAssumptions = assumptions.filter((a) =>
              ds.relatedAssumptionKeys.includes(a.key)
            );

            return (
              <Card key={ds.domain} className="border-slate-800 bg-slate-900/90" data-testid={`forecast-card-${ds.domain}`}>
                <CardHeader className="pb-2">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-base text-white">{ds.title}</CardTitle>
                        <Badge variant="outline" className="capitalize">
                          {ds.domain}
                        </Badge>
                      </div>
                      <CardDescription className="text-xs text-slate-400 mt-1">
                        {ds.description}
                      </CardDescription>
                    </div>

                    {/* Editable Assumption Links */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[11px] text-slate-500">Governing Assumptions:</span>
                      {relatedAssumptions.map((assump) => (
                        <button
                          key={assump.key}
                          data-testid={`edit-assumption-pill-${assump.key}`}
                          onClick={() => handleEditClick(assump)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-700 bg-slate-800 text-[11px] font-mono text-amber-300 hover:border-amber-400 transition-colors"
                        >
                          <span>{assump.key}={assump.value}{assump.unit ? assump.unit : ""}</span>
                          <Edit3 className="w-3 h-3 text-slate-400" />
                        </button>
                      ))}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-4">
                  <div className="h-72 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {ds.domain === "food" ? (
                        <BarChart data={ds.points} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} />
                          <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#0f172a",
                              borderColor: "#334155",
                              borderRadius: "8px",
                              fontSize: "12px",
                              color: "#f8fafc",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                          <ReferenceLine
                            y={2400}
                            label={{ value: "Vendor Prep Limit (2,400)", fill: "#f43f5e", fontSize: 11 }}
                            stroke="#f43f5e"
                            strokeDasharray="4 4"
                          />
                          <Bar
                            dataKey="confirmedDemand"
                            name="Confirmed Vouchers (PROJECTION)"
                            fill="#6366f1"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="assumedSurgeDemand"
                            name="Walk-in Buffer (ASSUMPTION)"
                            fill="#f59e0b"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      ) : (
                        <LineChart data={ds.points} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="timeLabel" stroke="#64748b" tick={{ fontSize: 11 }} />
                          <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "#0f172a",
                              borderColor: "#334155",
                              borderRadius: "8px",
                              fontSize: "12px",
                              color: "#f8fafc",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
                          <ReferenceLine
                            y={ds.domain === "accommodation" ? 1450 : 48}
                            label={{
                              value: ds.domain === "accommodation" ? "Max Beds (1,450)" : "Loop Fleet Limit (48)",
                              fill: "#f43f5e",
                              fontSize: 11,
                            }}
                            stroke="#f43f5e"
                            strokeDasharray="4 4"
                          />
                          <Line
                            type="monotone"
                            dataKey="confirmedDemand"
                            name="Confirmed Demand (PROJECTION)"
                            stroke="#6366f1"
                            strokeWidth={2.5}
                            dot={{ r: 3 }}
                          />
                          <Line
                            type="monotone"
                            dataKey="projectedTotalDemand"
                            name="Projected Total with Heuristic (ASSUMPTION)"
                            stroke="#f59e0b"
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            dot={{ r: 3 }}
                          />
                        </LineChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Assumptions Summary Catalog */}
      <Card className="border-slate-800 bg-slate-900/70" data-testid="assumptions-table-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Registered FestOS Operational Assumptions ({assumptions.length})
          </CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Every heuristic assumption is visible, editable, owned, and sourced. Schedules generated are strictly labelled ASSUMED.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-xs text-left border-collapse">
              <thead className="bg-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="p-3">Assumption Key</th>
                  <th className="p-3">Label & Description</th>
                  <th className="p-3">Current Value</th>
                  <th className="p-3">Owner</th>
                  <th className="p-3">Source & Reason</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/60 font-mono">
                {assumptions.map((item) => (
                  <tr key={item.key} className="hover:bg-slate-800/40">
                    <td className="p-3 text-indigo-300 font-bold">{item.key}</td>
                    <td className="p-3 font-sans text-slate-200">
                      <div>{item.label}</div>
                      <div className="text-[11px] text-slate-400 font-sans">{item.impactIfChanged}</div>
                    </td>
                    <td className="p-3 font-bold text-amber-300">
                      {item.value} {item.unit || ""}
                    </td>
                    <td className="p-3 font-sans text-slate-300">{item.owner}</td>
                    <td className="p-3 font-sans text-slate-400 text-[11px]">{item.reason}</td>
                    <td className="p-3 text-right font-sans">
                      <Button
                        data-testid={`table-edit-${item.key}`}
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditClick(item)}
                        className="text-xs"
                      >
                        <Edit3 className="w-3 h-3 mr-1" /> Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Edit Assumption Modal */}
      {editingAssumption && (
        <Modal
          isOpen={true}
          onClose={() => setEditingAssumption(null)}
          title={`Edit Heuristic Assumption: ${editingAssumption.key}`}
          size="md"
        >
          <div className="space-y-4 text-xs" data-testid="edit-assumption-modal">
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
              <div className="font-semibold text-white">{editingAssumption.label}</div>
              <div className="text-slate-400">
                <strong>Source:</strong> {editingAssumption.source} · <strong>Owner:</strong> {editingAssumption.owner}
              </div>
              <div className="text-amber-300/90 pt-1">
                <strong>Impact if Changed:</strong> {editingAssumption.impactIfChanged}
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">
                New Assumption Value ({editingAssumption.unit || "scalar"}) <span className="text-rose-400">*</span>
              </label>
              <input
                data-testid="assumption-value-input"
                type="text"
                value={newAssumptionValue}
                onChange={(e) => setNewAssumptionValue(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">
                Mandatory Operational Rationale <span className="text-rose-400">*</span>
              </label>
              <textarea
                data-testid="assumption-reason-input"
                rows={3}
                placeholder="Under FestOS principles, record explicit reason and authority for modifying this assumption..."
                value={updateReason}
                onChange={(e) => setUpdateReason(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button variant="outline" size="sm" onClick={() => setEditingAssumption(null)}>
                Cancel
              </Button>
              <Button
                data-testid="save-assumption-btn"
                variant="primary"
                size="sm"
                onClick={handleSaveAssumption}
                disabled={!updateReason.trim()}
              >
                Save & Recalculate
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ForecastingWorkspace;
