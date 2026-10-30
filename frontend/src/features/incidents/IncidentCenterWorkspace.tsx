import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { ScenarioDefinition, IncidentRecord } from "./types";
import { SCENARIO_DEFINITIONS } from "./scenarios_data";
import { DisruptionFlowModal } from "./DisruptionFlowModal";
import { SeverityPill } from "../../components/ui/SeverityPill";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import {
  AlertTriangle,
  Play,
  Flame,
  ShieldAlert,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Link } from "react-router-dom";

export const IncidentCenterWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedScenario, setSelectedScenario] = useState<ScenarioDefinition | null>(null);
  const [isFlowModalOpen, setIsFlowModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [showExtras, setShowExtras] = useState(false);

  // 1. Fetch Incidents List
  const { data: incidentsData, refetch: refetchIncidents } = useQuery<{ items: IncidentRecord[]; total: number }>({
    queryKey: ["incidents_list"],
    queryFn: async () => {
      const res = await api.get<{ items: IncidentRecord[]; total: number }>("/api/v1/incidents");
      return res;
    },
    refetchInterval: 10000,
  });

  // 2. Fetch Concurrent Warning Banner
  const { data: concurrentWarning } = useQuery<{
    has_concurrent_incidents: boolean;
    active_count: number;
    message: string | null;
  }>({
    queryKey: ["concurrent_incidents_warning"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/incidents/concurrent-warning");
      return res;
    },
    refetchInterval: 10000,
  });

  const primaryScenarios = SCENARIO_DEFINITIONS.filter((s) => s.isPrimary);
  const extraScenarios = SCENARIO_DEFINITIONS.filter((s) => !s.isPrimary);

  const incidents = incidentsData?.items || [];
  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter !== "ALL" && inc.status !== statusFilter) return false;
    return true;
  });

  const handleLaunchScenario = (sc: ScenarioDefinition) => {
    setSelectedScenario(sc);
    setIsFlowModalOpen(true);
  };

  const handleIncidentResolved = () => {
    queryClient.invalidateQueries({ queryKey: ["incidents_list"] });
    queryClient.invalidateQueries({ queryKey: ["concurrent_incidents_warning"] });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-600/20 text-red-400">
              <Flame className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Incident Center & Disruption Console</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time live-test disruption injector, multi-plan impact evaluator, and downstream synchronization ledger.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link to="/impact">
            <Button variant="secondary" size="sm">
              Impact Tree Analysis <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={() => refetchIncidents()} title="Refresh incident list">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Concurrent Incidents Warning Banner */}
      {concurrentWarning?.has_concurrent_incidents && (
        <div
          className="rounded-xl border border-amber-500/50 bg-amber-950/30 p-4 shadow-lg backdrop-blur flex items-start space-x-3"
          data-testid="concurrent-incident-banner"
        >
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-300">
                Warning: Multiple Concurrent Disruptions Active ({concurrentWarning.active_count})
              </span>
              <Badge status="PENDING">CROSS-RESOURCE CONTENTION</Badge>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed">
              {concurrentWarning.message ||
                "Simultaneous incidents in progress. Transport fleet and volunteer escorts may experience resource contention across Accommodation and Event corridors."}
            </p>
          </div>
        </div>
      )}

      {/* Section 1: The 7 Mandatory Live-Test Scenario Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 text-indigo-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Seven Live-Test Scenario Cards (Prompt 13 Mandatory Drills)
            </h2>
          </div>
          <span className="text-[11px] text-slate-500">Keyboard navigation: Enter to advance flows</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {primaryScenarios.map((scenario) => (
            <div
              key={scenario.id}
              data-testid={`scenario-card-${scenario.id}`}
              className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-4 shadow-sm hover:border-slate-700 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40">
                    {scenario.category}
                  </span>
                  <SeverityPill severity={scenario.defaultSeverity} />
                </div>

                <div>
                  <h3 className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">
                    {scenario.title}
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-3 leading-relaxed">
                    {scenario.description}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-[10px] text-slate-500">Guided Flow</span>
                <Button
                  variant="primary"
                  size="sm"
                  className="text-xs"
                  onClick={() => handleLaunchScenario(scenario)}
                  data-testid={`launch-btn-${scenario.id}`}
                >
                  <Play className="mr-1.5 h-3 w-3 fill-current" /> Inject Disruption
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Extras (Secondary List) Accordion */}
      <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4">
        <button
          onClick={() => setShowExtras(!showExtras)}
          className="flex w-full items-center justify-between text-left text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-white transition-colors"
          data-testid="toggle-extras-btn"
        >
          <div className="flex items-center space-x-2">
            <Sparkles className="h-4 w-4 text-amber-400" />
            <span>Additional Disruption Scenarios (Secondary Catalog - 5 Scenarios)</span>
          </div>
          {showExtras ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {showExtras && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-3 border-t border-slate-800">
            {extraScenarios.map((extra) => (
              <div
                key={extra.id}
                className="rounded-lg border border-slate-800/80 bg-slate-900/60 p-3 flex flex-col justify-between"
                data-testid={`scenario-extra-${extra.id}`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[9px] uppercase font-bold text-slate-400">{extra.category}</span>
                    <SeverityPill severity={extra.defaultSeverity} />
                  </div>
                  <h4 className="text-xs font-bold text-white">{extra.title}</h4>
                  <p className="text-[10px] text-slate-400 mt-1 line-clamp-2">{extra.description}</p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-800/60 flex justify-end">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="text-[11px] h-7"
                    onClick={() => handleLaunchScenario(extra)}
                  >
                    <Play className="mr-1 h-2.5 w-2.5 fill-current" /> Inject Extra
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 2: Incident Register & Timeline */}
      <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 text-indigo-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Incident Register & Historical Timeline
            </h2>
            <Badge status="ACTIVE">{filteredIncidents.length}</Badge>
          </div>

          <div className="flex items-center space-x-2">
            {/* Filter Buttons */}
            {["ALL", "ACTIVE", "INVESTIGATING", "RESOLVED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-all ${
                  statusFilter === st
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Incident List Table */}
        <div className="space-y-3" data-testid="incident-timeline-list">
          {filteredIncidents.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No incidents matching filter. Inject a disruption scenario from the cards above.
            </div>
          ) : (
            filteredIncidents.map((incident) => (
              <div
                key={incident.id}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 transition-all hover:border-slate-700 flex flex-col md:flex-row md:items-center justify-between gap-4"
                data-testid={`incident-row-${incident.id}`}
              >
                <div className="space-y-1.5 max-w-2xl">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-bold text-slate-400">{incident.id}</span>
                    <SeverityPill severity={incident.severity} />
                    <Badge
                      status={
                        incident.status === "RESOLVED"
                          ? "SUCCESS"
                          : incident.status === "ACTIVE"
                          ? "REJECTED"
                          : "PENDING"
                      }
                    >
                      {incident.status}
                    </Badge>
                  </div>

                  <h4 className="text-sm font-bold text-white">{incident.title}</h4>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 pt-1">
                    <span className="flex items-center">
                      <Clock className="mr-1 h-3 w-3" />
                      {new Date(incident.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                    <span>•</span>
                    <span className="font-mono text-amber-400 font-semibold">
                      {incident.peopleAffected} People Affected
                    </span>
                    {incident.approvedPlan && (
                      <>
                        <span>•</span>
                        <span className="text-indigo-300">Plan: {incident.approvedPlan}</span>
                      </>
                    )}
                    {incident.approvedBy && (
                      <>
                        <span>•</span>
                        <span className="text-slate-500">Auth: {incident.approvedBy}</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Link to={`/impact?incident_id=${incident.id}`}>
                    <Button variant="secondary" size="sm" className="text-xs">
                      Blast Radius <ArrowRight className="ml-1 h-3 w-3" />
                    </Button>
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Disruption Guided Flow Modal */}
      <DisruptionFlowModal
        scenario={selectedScenario}
        isOpen={isFlowModalOpen}
        onClose={() => setIsFlowModalOpen(false)}
        onIncidentResolved={handleIncidentResolved}
      />
    </div>
  );
};

export default IncidentCenterWorkspace;
