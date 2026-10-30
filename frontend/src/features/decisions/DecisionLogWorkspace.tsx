import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  Badge,
  Button,
  Drawer,
} from "../../components/ui";
import { DecisionCardItem } from "./types";
import { api } from "../../api/client";

export const DecisionLogWorkspace: React.FC = () => {
  const navigate = useNavigate();

  const [selectedModule, setSelectedModule] = useState<string>("all");
  const [selectedApprover, setSelectedApprover] = useState<string>("all");
  const [selectedWhyCard, setSelectedWhyCard] = useState<DecisionCardItem | null>(null);

  // 1. Fetch Decision Log
  const { data: decisionsData, isLoading } = useQuery<{
    data: { items: DecisionCardItem[]; total: number };
  }>({
    queryKey: ["decisions", "list", selectedModule, selectedApprover],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedModule !== "all") params.append("module", selectedModule);
      if (selectedApprover !== "all") params.append("approver", selectedApprover);
      const qs = params.toString();
      return api.get(qs ? `/api/v1/decisions?${qs}` : "/api/v1/decisions");
    },
  });

  const decisions: DecisionCardItem[] =
    (decisionsData as any)?.items || (decisionsData as any)?.data?.items || [];

  return (
    <div className="space-y-6" data-testid="decision-log-workspace">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">Decision Log & Why Cards</h1>
            <Badge variant="solid" status="SUCCESS">
              AUDIT TRAIL
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Immutable register of festival director approvals, constraint relaxations, and rejected alternatives under FestOS governance.
          </p>
        </div>

        {/* Link to Override Register */}
        <div className="flex items-center gap-2">
          <Button
            data-testid="override-register-link-btn"
            variant="outline"
            size="sm"
            onClick={() => navigate("/overrides")}
            className="border-amber-500/40 text-amber-300 hover:bg-amber-950/30"
          >
            <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-400" />
            Override Register →
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-slate-800 bg-slate-900/80 text-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-semibold text-slate-300">Filter By Domain:</span>
          <select
            data-testid="filter-module-select"
            value={selectedModule}
            onChange={(e) => setSelectedModule(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-slate-200 focus:outline-none"
          >
            <option value="all">All Domains</option>
            <option value="accommodation">Accommodation</option>
            <option value="vendors">Vendors & Food</option>
            <option value="schedule">Schedule & Venues</option>
            <option value="transport">Transport</option>
            <option value="incidents">Disruptions</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-300">Approver Role:</span>
          <select
            data-testid="filter-approver-select"
            value={selectedApprover}
            onChange={(e) => setSelectedApprover(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-slate-200 focus:outline-none"
          >
            <option value="all">All Approvers</option>
            <option value="FESTIVAL_DIRECTOR">Festival Director</option>
            <option value="FOOD_OPS_MANAGER">Food Ops Manager</option>
            <option value="EVENT_LEAD">Event Lead</option>
            <option value="ACCOMMODATION_LEAD">Accommodation Lead</option>
          </select>
        </div>

        <div className="text-slate-500 font-mono">
          Showing {decisions.length} recorded decision{decisions.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Decisions Table */}
      <Card className="border-slate-800 bg-slate-900/90">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-xs">Loading decision cards...</div>
          ) : decisions.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              No decisions recorded matching the selected filter criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse" data-testid="decisions-table">
                <thead className="bg-slate-800/80 text-slate-400 font-medium">
                  <tr>
                    <th className="p-3">Decision ID</th>
                    <th className="p-3">Subject / Title</th>
                    <th className="p-3">Module</th>
                    <th className="p-3">Approver</th>
                    <th className="p-3 text-right">People Affected</th>
                    <th className="p-3 text-right">Cost Impact (INR)</th>
                    <th className="p-3 text-center">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-900/60 font-mono">
                  {decisions.map((dec) => (
                    <tr key={dec.id} className="hover:bg-slate-800/40" data-testid={`decision-row-${dec.id}`}>
                      <td className="p-3 font-bold text-indigo-300">{dec.id}</td>
                      <td className="p-3 font-sans font-medium text-white max-w-xs">
                        <div className="font-semibold">{dec.title}</div>
                        <div className="text-[11px] text-slate-400 line-clamp-1">{dec.summary}</div>
                      </td>
                      <td className="p-3 font-sans capitalize text-slate-300">
                        <Badge variant="outline">{dec.module}</Badge>
                      </td>
                      <td className="p-3 font-sans text-slate-200">
                        <div>{dec.approverName}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{dec.approverRole}</div>
                      </td>
                      <td className="p-3 text-right text-slate-300 font-bold">
                        {dec.peopleAffected > 0 ? `${dec.peopleAffected}p` : "—"}
                      </td>
                      <td className="p-3 text-right font-bold text-emerald-400">
                        {dec.costImpactInr > 0 ? `₹${dec.costImpactInr.toLocaleString()}` : "₹0"}
                      </td>
                      <td className="p-3 text-center font-sans">
                        <Badge
                          variant="solid"
                          status={dec.status === "RECORDED" ? "SUCCESS" : "PENDING"}
                        >
                          {dec.status}
                        </Badge>
                      </td>
                      <td className="p-3 text-right font-sans">
                        <Button
                          data-testid={`why-card-btn-${dec.id}`}
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedWhyCard(dec)}
                          className="text-xs"
                        >
                          <HelpCircle className="w-3.5 h-3.5 mr-1 text-indigo-400" />
                          Why?
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Why Card Drawer */}
      {selectedWhyCard && (
        <Drawer
          isOpen={true}
          onClose={() => setSelectedWhyCard(null)}
          title={`Why Card: ${selectedWhyCard.id}`}
          width="max-w-md"
        >
          <div className="space-y-5 text-xs" data-testid="why-card-drawer">
            {/* Header info */}
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
              <div className="font-bold text-white text-sm">{selectedWhyCard.title}</div>
              <div className="text-slate-400">
                Approved by <strong>{selectedWhyCard.approverName}</strong> ({selectedWhyCard.approverRole})
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Timestamp: {selectedWhyCard.createdAt} · ChangeSet: {selectedWhyCard.changeSetId || "cs_live"}
              </div>
            </div>

            {/* Core Rationale */}
            <div className="space-y-1.5">
              <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">
                Operational Rationale & Recommendation
              </h4>
              <p className="text-slate-200 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                {selectedWhyCard.why}
              </p>
            </div>

            {/* Hard Constraints Satisfied */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs">
                <CheckCircle2 className="w-4 h-4" />
                <span>Hard Constraints Satisfied (Never Auto-Relaxed)</span>
              </div>
              <div className="space-y-1.5">
                {selectedWhyCard.hardConstraintsSatisfied.map((hc, idx) => (
                  <div key={idx} className="p-2 rounded bg-emerald-950/20 border border-emerald-900/40 text-emerald-200 text-[11px]">
                    ✓ {hc}
                  </div>
                ))}
              </div>
            </div>

            {/* Soft Constraints Relaxed under Ladder */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-xs">
                <AlertTriangle className="w-4 h-4" />
                <span>Soft Constraints Relaxed (Ladder Order)</span>
              </div>
              {selectedWhyCard.softConstraintsRelaxed.length === 0 ? (
                <div className="text-slate-500 text-[11px] italic">No soft constraints relaxed.</div>
              ) : (
                <div className="space-y-2">
                  {selectedWhyCard.softConstraintsRelaxed.map((sc, idx) => (
                    <div key={idx} className="p-2.5 rounded bg-amber-950/20 border border-amber-900/40 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-amber-200">{sc.constraint}</span>
                        <span className="font-mono text-[10px] text-amber-400">
                          Ladder Rung: {sc.ladderPriority === 1 ? "Cohesion" : sc.ladderPriority === 2 ? "Cost" : "Proximity"}
                        </span>
                      </div>
                      <div className="text-slate-300 text-[11px]">{sc.rationale}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Alternatives Rejected */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-slate-300 font-semibold text-xs">
                <XCircle className="w-4 h-4 text-slate-500" />
                <span>Alternatives Rejected (Why Not?)</span>
              </div>
              <div className="space-y-2">
                {selectedWhyCard.alternativesRejected.map((alt, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1">
                    <div className="font-semibold text-white">{alt.option}</div>
                    <div className="text-slate-400 text-[11px]">
                      <strong>Rejected Rationale:</strong> {alt.why}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Financial & Human Impact */}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-center font-mono">
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-sans">People Affected</span>
                <span className="text-sm font-bold text-white">{selectedWhyCard.peopleAffected}</span>
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-500 block font-sans">Cost Delta</span>
                <span className="text-sm font-bold text-emerald-400">
                  ₹{selectedWhyCard.costImpactInr.toLocaleString()}
                </span>
              </div>
            </div>

            {selectedWhyCard.overrideId && (
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-center border-amber-500/40 text-amber-300"
                  onClick={() => {
                    setSelectedWhyCard(null);
                    navigate("/overrides");
                  }}
                >
                  Inspect Override #{selectedWhyCard.overrideId} in Register →
                </Button>
              </div>
            )}
          </div>
        </Drawer>
      )}
    </div>
  );
};

export default DecisionLogWorkspace;
