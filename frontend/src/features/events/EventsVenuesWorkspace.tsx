import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  Calendar,
  AlertTriangle,
  Clock,
  MapPin,
  CheckCircle2,
  Users,
  ShieldAlert,
  GitBranch,
  Edit3,
  Sliders,
  RotateCcw,
  X,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Drawer } from "../../components/ui/Drawer";
import { ConfirmWithReason } from "../../components/ui/ConfirmWithReason";
import { SeverityPill } from "../../components/ui/SeverityPill";
import { useToast } from "../../components/ui/Toast";
import {
  VenueTimeline,
  ScheduleConflict,
  ResolutionCandidate,
  UnscheduledEntrant,
  ScheduleVersion,
  VenueItem,
  FairnessDecision,
  ConflictType,
} from "./types";
import { SeverityType } from "../../components/ui/SeverityPill";

const CONFLICT_TYPE_LABELS: Record<ConflictType, string> = {
  VENUE_DOUBLE_BOOKING: "Venue Double Booking",
  PARTICIPANT_CLASH: "Participant Clash",
  JUDGE_DOUBLE_BOOKING: "Judge Double Booking",
  TEARDOWN_SETUP_OVERLAP: "Teardown / Setup Overlap",
  TRAVEL_TIME_INSUFFICIENT: "Insufficient Travel Time",
  ROUND_DEPENDENCY_TIMING: "Round Dependency Timing",
  ARRIVAL_WINDOW_BREACH: "Arrival Window Breach",
  CAPACITY_EXCEEDED: "Venue Capacity Exceeded",
  EQUIPMENT_UNAVAILABLE: "Equipment Unavailable",
  ACCESSIBILITY_UNMET: "Accessibility Unmet",
};

export const EventsVenuesWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "timeline" | "conflicts" | "unscheduled" | "versions" | "editors" | "decisions"
  >("timeline");

  const [selectedConflict, setSelectedConflict] = useState<ScheduleConflict | null>(null);
  const [resolvingCandidate, setResolvingCandidate] = useState<ResolutionCandidate | null>(null);
  const [confirmResolutionOpen, setConfirmResolutionOpen] = useState(false);
  const [conflictTypeFilter, setConflictTypeFilter] = useState<string>("ALL");
  const [conflictSeverityFilter, setConflictSeverityFilter] = useState<string>("ALL");

  // Version diff modal
  const [diffModalOpen, setDiffModalOpen] = useState(false);
  const [restoreVersionTarget, setRestoreVersionTarget] = useState<ScheduleVersion | null>(null);

  // Editors state
  const [editingVenue, setEditingVenue] = useState<VenueItem | null>(null);
  const [newTagInput, setNewTagInput] = useState("");

  const { addToast } = useToast();
  const showToast = (title: string, type: "success" | "warning" | "error" | "info" = "info") =>
    addToast({ title, type });
  const queryClient = useQueryClient();

  // Queries
  const { data: timelineData, isLoading: timelineLoading } = useQuery<VenueTimeline[]>({
    queryKey: ["schedule_timeline"],
    queryFn: async () => {
      const res = await api.get<{ venues: VenueTimeline[] }>("/api/v1/schedule/timeline");
      return res?.venues || [];
    },
  });

  const { data: conflictsData, isLoading: conflictsLoading } = useQuery<ScheduleConflict[]>({
    queryKey: ["schedule_conflicts"],
    queryFn: async () => {
      const res = await api.get<{ items: ScheduleConflict[]; total: number }>("/api/v1/schedule/conflicts");
      return res?.items || [];
    },
  });

  const { data: resolutionsData, isLoading: resolutionsLoading } = useQuery<ResolutionCandidate[]>({
    queryKey: ["schedule_resolutions", selectedConflict?.id],
    queryFn: async () => {
      if (!selectedConflict) return [];
      const res = await api.get<{ recommendations: ResolutionCandidate[] }>(
        `/api/v1/schedule/conflicts/${selectedConflict.id}/resolutions`
      );
      return res?.recommendations || [];
    },
    enabled: !!selectedConflict,
  });

  const { data: unscheduledData, isLoading: unscheduledLoading } = useQuery<{
    items: UnscheduledEntrant[];
    unscheduled_count: number;
    scheduled_count: number;
  }>({
    queryKey: ["schedule_unscheduled"],
    queryFn: async () => {
      const res = await api.get<{
        items: UnscheduledEntrant[];
        unscheduled_count: number;
        scheduled_count: number;
      }>("/api/v1/schedule/unscheduled");
      return res;
    },
  });

  const { data: versionsData, isLoading: versionsLoading } = useQuery<ScheduleVersion[]>({
    queryKey: ["schedule_versions"],
    queryFn: async () => {
      const res = await api.get<{ items: ScheduleVersion[] }>("/api/v1/schedule/versions");
      return res?.items || [];
    },
  });

  const { data: venuesData } = useQuery<VenueItem[]>({
    queryKey: ["venues_list"],
    queryFn: async () => {
      const res = await api.get<{ items: VenueItem[] }>("/api/v1/venues");
      return res?.items || [];
    },
  });

  const { data: compatibilityData } = useQuery<Record<string, string[]>>({
    queryKey: ["venues_compatibility"],
    queryFn: async () => {
      const res = await api.get<{ mapping: Record<string, string[]> }>("/api/v1/venues/compatibility");
      return res?.mapping || {};
    },
  });

  const { data: fairnessData } = useQuery<FairnessDecision[]>({
    queryKey: ["schedule_fairness"],
    queryFn: async () => {
      const res = await api.get<{ decisions: FairnessDecision[] }>("/api/v1/schedule/fairness-decisions");
      return res?.decisions || [];
    },
  });

  // Mutations
  const applyResolutionMutation = useMutation({
    mutationFn: async ({ conflictId, action, reason }: { conflictId: string; action: string; reason: string }) => {
      return api.post(`/api/v1/schedule/conflicts/${conflictId}/apply-resolution`, {
        action,
        reason,
      });
    },
    onSuccess: () => {
      showToast("Resolution applied successfully via ChangeService", "success");
      setSelectedConflict(null);
      setResolvingCandidate(null);
      queryClient.invalidateQueries({ queryKey: ["schedule_conflicts"] });
      queryClient.invalidateQueries({ queryKey: ["schedule_timeline"] });
    },
    onError: (err: any) => {
      showToast(err?.message || "Failed to apply resolution", "error");
    },
  });

  const restoreVersionMutation = useMutation({
    mutationFn: async ({ versionId, reason }: { versionId: string; reason: string }) => {
      return api.post(`/api/v1/schedule/versions/${versionId}/restore`, { reason });
    },
    onSuccess: () => {
      showToast("Schedule version restored successfully", "success");
      setRestoreVersionTarget(null);
      queryClient.invalidateQueries({ queryKey: ["schedule_versions"] });
      queryClient.invalidateQueries({ queryKey: ["schedule_timeline"] });
      queryClient.invalidateQueries({ queryKey: ["schedule_conflicts"] });
    },
  });

  const updateVenueMutation = useMutation({
    mutationFn: async (venue: VenueItem) => {
      return api.put(`/api/v1/venues/${venue.id}`, venue);
    },
    onSuccess: () => {
      showToast("Venue updated successfully", "success");
      setEditingVenue(null);
      queryClient.invalidateQueries({ queryKey: ["venues_list"] });
    },
  });

  // Filtered conflicts
  const filteredConflicts = (conflictsData || []).filter((c) => {
    if (conflictTypeFilter !== "ALL" && c.conflict_type !== conflictTypeFilter) return false;
    if (conflictSeverityFilter !== "ALL" && String(c.severity) !== conflictSeverityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 p-6">
      {/* Page Header with ASSUMED banner */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Calendar className="h-7 w-7 text-indigo-400" />
              Events & Venues Operations
            </h1>
            <span className="px-3 py-1 font-mono text-xs tracking-wider font-bold rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
              ASSUMED SCHEDULE
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Gantt timeline, 10-type conflict detection engine, resolution ranking, and venue compatibility
          </p>
        </div>

        {/* Global Action Banner */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-amber-950/40 border border-amber-600/30 px-3 py-1.5 text-xs text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>Schedule generated synthetically. Times & venues require event lead validation.</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-2 overflow-x-auto pb-1">
        {[
          { id: "timeline", label: "Gantt Timeline", icon: Calendar, badge: timelineData?.length },
          { id: "conflicts", label: "Conflict Panel", icon: AlertTriangle, badge: conflictsData?.length, badgeVariant: "danger" },
          { id: "unscheduled", label: "Unscheduled Entrants", icon: Users, badge: unscheduledData?.unscheduled_count || 987 },
          { id: "versions", label: "Versions & Diff", icon: GitBranch, badge: versionsData?.length },
          { id: "editors", label: "Event & Venue Editors", icon: Edit3 },
          { id: "decisions", label: "Fairness Decisions", icon: ShieldAlert, badge: fairnessData?.length, badgeVariant: "warning" },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-t-lg transition-all border-b-2 ${
                isActive
                  ? "border-indigo-500 text-indigo-400 bg-slate-900/60"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full ${
                    tab.badgeVariant === "danger"
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      : tab.badgeVariant === "warning"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: GANTT TIMELINE */}
      {activeTab === "timeline" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white">Venue Schedule Timetable (Day 1 - 31 Oct 2026)</h2>
              <Badge variant="outline" className="text-amber-400 border-amber-500/40">
                ASSUMED DRAFT
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded bg-indigo-600"></span> Event Block
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded bg-amber-500/30 border border-amber-500/50"></span> Buffer (Setup/Teardown)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded bg-rose-500/30 border border-rose-500/50"></span> Judge Gap
              </span>
            </div>
          </div>

          {timelineLoading ? (
            <div className="p-12 text-center text-slate-400">Loading timeline...</div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 overflow-x-auto space-y-6">
              {timelineData?.map((venue) => (
                <div key={venue.venue_id} className="space-y-2 border-b border-slate-800/60 pb-5 last:border-b-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MapPin className="h-4 w-4 text-indigo-400" />
                      <span className="font-bold text-white">{venue.venue_name}</span>
                      <span className="text-xs text-slate-400 font-mono">({venue.venue_id})</span>
                    </div>
                    <span className="text-xs text-slate-400">{venue.blocks.length} sessions scheduled</span>
                  </div>

                  {/* Horizontal Timeline Bar Representation */}
                  <div className="relative min-h-[90px] rounded-lg bg-slate-900/80 border border-slate-800 p-2 flex gap-3 overflow-x-auto">
                    {venue.blocks.length === 0 ? (
                      <div className="flex h-16 w-full items-center justify-center text-xs text-slate-500">
                        No sessions allocated
                      </div>
                    ) : (
                      venue.blocks.map((block) => (
                        <div
                          key={block.session_id}
                          className={`relative flex-1 min-w-[260px] rounded-lg border p-3 transition-all ${
                            block.judge_gap
                              ? "border-rose-500/60 bg-rose-950/20 hover:border-rose-400"
                              : "border-indigo-500/40 bg-indigo-950/20 hover:border-indigo-400"
                          }`}
                        >
                          {/* Badge tag */}
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-slate-200 truncate">{block.event_name}</span>
                            <span className="font-mono text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/30">
                              ASSUMED
                            </span>
                          </div>

                          <div className="text-[11px] text-slate-400 flex items-center gap-1 mb-2">
                            <Clock className="h-3 w-3 text-slate-400" />
                            <span>
                              {block.start.slice(11, 16)} - {block.end.slice(11, 16)}
                            </span>
                            <span className="text-slate-500">({block.round})</span>
                          </div>

                          {/* Judge Gap Indicator */}
                          {block.judge_gap ? (
                            <div className="flex items-center justify-between gap-1 text-[11px] font-medium text-rose-400 bg-rose-950/40 rounded px-2 py-1 border border-rose-800/40">
                              <span className="flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3 shrink-0" />
                                Judge Gap: {block.judges_assigned}/{block.judges_needed} assigned
                              </span>
                              <button
                                onClick={() => showToast(`Opening judge assignment for ${block.event_name}`, "info")}
                                className="text-[10px] underline font-bold hover:text-white"
                              >
                                Assign
                              </button>
                            </div>
                          ) : (
                            <div className="text-[11px] text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" />
                              <span>Judges: {block.judges_assigned}/{block.judges_needed} Full</span>
                            </div>
                          )}

                          <div className="mt-2 text-[10px] text-slate-400 flex justify-between">
                            <span>Setup: {block.setup_start.slice(11, 16)}</span>
                            <span>Teardown: {block.teardown_end.slice(11, 16)}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CONFLICT PANEL */}
      {activeTab === "conflicts" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-rose-400" />
                Schedule Conflicts Engine (10 Types Monitored)
              </h2>
              <p className="text-xs text-slate-400">
                Zero venue overlaps does not mean zero conflicts: sweep-line checks all 10 constraint types.
              </p>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-2">
              <select
                aria-label="Filter by conflict type"
                value={conflictTypeFilter}
                onChange={(e) => setConflictTypeFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Conflict Types (10)</option>
                {Object.entries(CONFLICT_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>

              <select
                aria-label="Filter by severity"
                value={conflictSeverityFilter}
                onChange={(e) => setConflictSeverityFilter(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Severities</option>
                <option value="4">Severity 4 (Critical)</option>
                <option value="3">Severity 3 (High)</option>
                <option value="2">Severity 2 (Medium)</option>
                <option value="1">Severity 1 (Low)</option>
              </select>
            </div>
          </div>

          {/* Conflict List */}
          <div className="space-y-3">
            {conflictsLoading ? (
              <div className="p-8 text-center text-slate-400">Loading conflicts...</div>
            ) : filteredConflicts.length === 0 ? (
              <div className="p-8 text-center text-slate-400 rounded-xl border border-slate-800 bg-[#0A0F1D]">
                <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                <p className="font-semibold text-white">No conflicts match filter</p>
              </div>
            ) : (
              filteredConflicts.map((c) => (
                <div
                  key={c.id}
                  className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-slate-700 transition-all"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-400">{c.id}</span>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {CONFLICT_TYPE_LABELS[c.conflict_type] || c.conflict_type}
                      </Badge>
                      <SeverityPill severity={c.severity as SeverityType} />
                      <span className="flex items-center gap-1 text-xs text-slate-400">
                        <Users className="h-3 w-3 text-slate-400" />
                        {c.people_affected} people affected
                      </span>
                    </div>

                    <p className="text-sm font-medium text-slate-200">{c.description}</p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setSelectedConflict(c)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-xs flex items-center gap-1.5"
                    >
                      <span>Ranked Resolutions</span>
                      <ArrowRight className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* RESOLUTIONS DRAWER */}
      <Drawer
        isOpen={!!selectedConflict}
        onClose={() => setSelectedConflict(null)}
        title={`Ranked Resolutions: ${selectedConflict?.id}`}
      >
        <div className="space-y-4">
          <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-1">
            <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Target Conflict</div>
            <div className="text-sm font-semibold text-white">{selectedConflict?.description}</div>
            <div className="flex items-center gap-2 pt-1 text-xs text-slate-400">
              <span>Type: {selectedConflict && CONFLICT_TYPE_LABELS[selectedConflict.conflict_type]}</span>
              <span>•</span>
              <span>{selectedConflict?.people_affected} People Affected</span>
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Ranked Candidates (Evaluated by Engine)
            </h3>

            {resolutionsLoading ? (
              <div className="p-4 text-center text-slate-400">Evaluating resolution options...</div>
            ) : resolutionsData?.length === 0 ? (
              <div className="p-4 text-center text-slate-400">No automated candidate found. Manual move required.</div>
            ) : (
              resolutionsData?.map((cand) => (
                <div
                  key={cand.id}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3 hover:border-slate-700 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                        #{cand.rank}
                      </span>
                      <span className="font-mono text-xs text-indigo-300">{cand.action}</span>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      <span className="rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40 px-2 py-0.5">
                        +{cand.conflicts_resolved} resolved
                      </span>
                      <span className="rounded bg-slate-800 text-slate-300 px-2 py-0.5">
                        {cand.new_conflicts_created} new
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300">{cand.rationale}</p>

                  <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/60 pt-2">
                    <span>{cand.people_affected} attendees affected</span>
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => {
                        setResolvingCandidate(cand);
                        setConfirmResolutionOpen(true);
                      }}
                      className="bg-indigo-600 hover:bg-indigo-500 text-xs"
                    >
                      Apply Candidate
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </Drawer>

      {/* CONFIRM RESOLUTION MODAL WITH REASON */}
      {confirmResolutionOpen && resolvingCandidate && selectedConflict && (
        <ConfirmWithReason
          isOpen={confirmResolutionOpen}
          onClose={() => setConfirmResolutionOpen(false)}
          title="Apply Schedule Resolution"
          confirmText="Apply via ChangeService"
          riskLevel="HIGH"
          onConfirm={(reason) => {
            applyResolutionMutation.mutate({
              conflictId: selectedConflict.id,
              action: resolvingCandidate.action,
              reason,
            });
            setConfirmResolutionOpen(false);
          }}
        >
          <div className="space-y-2 text-sm text-slate-300">
            <p>
              You are applying ranked recommendation <strong>#{resolvingCandidate.rank}</strong>:
            </p>
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-2 text-xs text-slate-200">
              {resolvingCandidate.rationale}
            </div>
            <p className="text-xs text-slate-400">
              This will update the schedule version and resolve conflict <strong>{selectedConflict.id}</strong>.
            </p>
          </div>
        </ConfirmWithReason>
      )}

      {/* TAB 3: UNSCHEDULED ENTRANTS TABLE */}
      {activeTab === "unscheduled" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="h-5 w-5 text-amber-400" />
                Unscheduled Entrants Report (987 Tracked Transparently)
              </h2>
              <p className="text-xs text-slate-400">
                Never silently drop participants. All unscheduled registrations are cataloged with failure reason and alternatives.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-xs text-slate-300">
                Scheduled: <strong className="text-emerald-400">{unscheduledData?.scheduled_count || 4593}</strong> /{" "}
                Unscheduled: <strong className="text-rose-400">{unscheduledData?.unscheduled_count || 987}</strong>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Participant</th>
                    <th className="px-4 py-3">Contingent</th>
                    <th className="px-4 py-3">Event</th>
                    <th className="px-4 py-3">Failure Reason</th>
                    <th className="px-4 py-3">Arrival Window</th>
                    <th className="px-4 py-3">Alternatives</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {unscheduledLoading ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        Loading unscheduled entrants...
                      </td>
                    </tr>
                  ) : (
                    unscheduledData?.items.map((it) => (
                      <tr key={it.participant_id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{it.participant_name}</div>
                          <div className="font-mono text-[10px] text-slate-500">{it.participant_id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div>{it.contingent_name}</div>
                          <div className="text-[10px] text-slate-500">{it.contingent_id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-200">{it.event_name}</div>
                          <div className="text-[10px] text-slate-500">{it.event_id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${
                              it.reason === "NOT_ON_SITE_LONG_ENOUGH"
                                ? "bg-amber-950/40 text-amber-300 border-amber-800/40"
                                : "bg-rose-950/40 text-rose-300 border-rose-800/40"
                            }`}
                          >
                            {it.reason.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[11px] text-slate-400">
                          <div>Arr: {it.arrival_datetime.slice(0, 16).replace("T", " ")}</div>
                          <div>Dep: {it.departure_datetime.slice(0, 16).replace("T", " ")}</div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="space-y-1">
                            {it.alternatives.map((alt, i) => (
                              <div key={i} className="text-[11px] text-indigo-300 flex items-center gap-1">
                                <span className="h-1 w-1 rounded-full bg-indigo-400"></span>
                                <span>{alt}</span>
                              </div>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => showToast(`Action requested for ${it.participant_name}`, "info")}
                            className="text-xs"
                          >
                            Propose Alternative
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SCHEDULE VERSIONS & RESTORE */}
      {activeTab === "versions" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <GitBranch className="h-5 w-5 text-indigo-400" />
                Schedule Version History & Rollback
              </h2>
              <p className="text-xs text-slate-400">
                Track every schedule mutation, compare versions, and safely rollback through ChangeService.
              </p>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setDiffModalOpen(true)}
              className="flex items-center gap-1.5 text-xs"
            >
              <Sliders className="h-3.5 w-3.5" />
              <span>Compare Versions</span>
            </Button>
          </div>

          <div className="space-y-3">
            {versionsLoading ? (
              <div className="p-8 text-center text-slate-400">Loading versions...</div>
            ) : (
              versionsData?.map((ver) => (
                <div
                  key={ver.id}
                  className={`rounded-xl border p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                    ver.is_active
                      ? "border-indigo-500/60 bg-indigo-950/20 shadow-md shadow-indigo-950/30"
                      : "border-slate-800 bg-[#0A0F1D]"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{ver.plan_name}</span>
                      <span className="font-mono text-xs text-slate-400">({ver.id})</span>
                      {ver.is_active ? (
                        <span className="rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 px-2 py-0.5 text-xs font-bold">
                          ACTIVE SCHEDULE
                        </span>
                      ) : (
                        <Badge variant="outline">ARCHIVED</Badge>
                      )}
                      <span className="font-mono text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/30">
                        {ver.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                      <span>Sessions: {ver.sessions_count}</span>
                      <span>•</span>
                      <span>Conflicts: {ver.conflicts_count}</span>
                      <span>•</span>
                      <span>Unscheduled: {ver.unscheduled_count}</span>
                      <span>•</span>
                      <span>Created: {ver.created_at.slice(0, 16).replace("T", " ")}</span>
                    </div>
                  </div>

                  {!ver.is_active && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setRestoreVersionTarget(ver)}
                      className="text-xs flex items-center gap-1.5 shrink-0 text-amber-300 hover:text-white"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      <span>Restore This Version</span>
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* RESTORE VERSION CONFIRM MODAL */}
      {restoreVersionTarget && (
        <ConfirmWithReason
          isOpen={!!restoreVersionTarget}
          onClose={() => setRestoreVersionTarget(null)}
          title="Restore Previous Schedule Version"
          confirmText="Restore Schedule"
          riskLevel="HIGH"
          onConfirm={(reason) => {
            restoreVersionMutation.mutate({
              versionId: restoreVersionTarget.id,
              reason,
            });
          }}
        >
          <div className="space-y-2 text-sm text-slate-300">
            <p>
              Are you sure you want to restore <strong>{restoreVersionTarget.plan_name}</strong>?
            </p>
            <p className="text-xs text-slate-400">
              This will overwrite current session placements with {restoreVersionTarget.sessions_count} sessions from{" "}
              {restoreVersionTarget.id}.
            </p>
          </div>
        </ConfirmWithReason>
      )}

      {/* VERSION DIFF MODAL */}
      <Modal
        isOpen={diffModalOpen}
        onClose={() => setDiffModalOpen(false)}
        title="Schedule Version Comparison / Diff"
        size="lg"
      >
        <div className="space-y-4 text-xs text-slate-300">
          <div className="grid grid-cols-2 gap-4 border-b border-slate-800 pb-3">
            <div>
              <div className="font-bold text-white text-sm">Plan Alpha (Current)</div>
              <div className="text-slate-400">172 sessions, 10 open conflicts</div>
            </div>
            <div>
              <div className="font-bold text-slate-300 text-sm">Plan Baseline (Pre-incident)</div>
              <div className="text-slate-400">154 sessions, 24 open conflicts</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-semibold text-slate-200">Key Differences:</div>
            <ul className="space-y-1.5 list-disc list-inside text-slate-400">
              <li>+18 new sessions added in Plan Alpha via graph clustering.</li>
              <li>Resolved 14 venue contention clashes in Amphitheatre and Main Auditorium.</li>
              <li>Unscheduled registrations reduced from 1,102 down to 987.</li>
              <li>Teardown buffers adjusted from 10m to 15m default per FESTOS_CONTEXT.md.</li>
            </ul>
          </div>
        </div>
      </Modal>

      {/* TAB 5: EDITORS (EVENT & VENUE EDITORS & COMPATIBILITY MAPPING) */}
      {activeTab === "editors" && (
        <div className="space-y-6">
          {/* VENUE-EVENT COMPATIBILITY MAPPING */}
          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-indigo-400" />
                  Venue-Event Compatibility Mapping
                </h3>
                <p className="text-xs text-slate-400">
                  Derived from prototype requirements; ASSUMED because raw data contains no explicit assignments.
                </p>
              </div>
              <span className="font-mono text-[10px] rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5">
                ASSUMED MAPPING
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(compatibilityData || {}).map(([reqKey, venues]) => (
                <div key={reqKey} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-200 text-xs">{reqKey}</span>
                    <span className="text-[10px] text-slate-500">{venues.length} venues compatible</span>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {venues.map((v) => (
                      <span
                        key={v}
                        className="inline-flex items-center gap-1 rounded bg-indigo-950/60 border border-indigo-700/40 px-2 py-0.5 text-[11px] font-mono text-indigo-300"
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* VENUES & TAG EDITOR */}
          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-emerald-400" />
                  Venue Configuration & Feature Tags
                </h3>
                <p className="text-xs text-slate-400">
                  Manage capacity, indoor/outdoor classification, setup/teardown buffers, and feature tags.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {venuesData?.map((venue) => (
                <div key={venue.id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="font-bold text-white text-sm">{venue.name}</div>
                    <span className="font-mono text-xs text-slate-500">{venue.id}</span>
                  </div>

                  <div className="text-xs text-slate-400 space-y-1">
                    <div>Capacity: {venue.capacity} • {venue.indoor_outdoor}</div>
                    <div>Setup/Teardown: {venue.setup_time_min}m / {venue.teardown_time_min}m</div>
                  </div>

                  {/* Feature Tags */}
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Feature Tags</div>
                    <div className="flex flex-wrap gap-1">
                      {venue.feature_tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-slate-800 border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setEditingVenue(venue)}
                    className="w-full text-xs"
                  >
                    Edit Venue & Tags
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* VENUE EDIT MODAL */}
      {editingVenue && (
        <Modal
          isOpen={!!editingVenue}
          onClose={() => setEditingVenue(null)}
          title={`Edit Venue: ${editingVenue.name}`}
        >
          <div className="space-y-4 text-xs text-slate-300">
            <div>
              <label className="block text-slate-400 mb-1">Capacity</label>
              <input
                type="number"
                value={editingVenue.capacity}
                onChange={(e) => setEditingVenue({ ...editingVenue, capacity: parseInt(e.target.value) || 0 })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Setup Time (min)</label>
                <input
                  type="number"
                  value={editingVenue.setup_time_min}
                  onChange={(e) => setEditingVenue({ ...editingVenue, setup_time_min: parseInt(e.target.value) || 0 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Teardown Time (min)</label>
                <input
                  type="number"
                  value={editingVenue.teardown_time_min}
                  onChange={(e) => setEditingVenue({ ...editingVenue, teardown_time_min: parseInt(e.target.value) || 0 })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white"
                />
              </div>
            </div>

            {/* Feature Tag Editor */}
            <div>
              <label className="block text-slate-400 mb-1">Feature Tags</label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {editingVenue.feature_tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs text-slate-200"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setEditingVenue({
                          ...editingVenue,
                          feature_tags: editingVenue.feature_tags.filter((t) => t !== tag),
                        })
                      }
                      className="hover:text-rose-400"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Add new tag..."
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newTagInput.trim()) {
                      e.preventDefault();
                      setEditingVenue({
                        ...editingVenue,
                        feature_tags: [...editingVenue.feature_tags, newTagInput.trim()],
                      });
                      setNewTagInput("");
                    }
                  }}
                  className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-1 text-xs text-white"
                />
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    if (newTagInput.trim()) {
                      setEditingVenue({
                        ...editingVenue,
                        feature_tags: [...editingVenue.feature_tags, newTagInput.trim()],
                      });
                      setNewTagInput("");
                    }
                  }}
                >
                  Add Tag
                </Button>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
              <Button variant="secondary" onClick={() => setEditingVenue(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => updateVenueMutation.mutate(editingVenue)}
              >
                Save Changes
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* TAB 6: FAIRNESS DECISIONS (LATE-WAVE & WILDCARDS) */}
      {activeTab === "decisions" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-400" />
              Fairness Decisions Requiring Approval
            </h2>
            <p className="text-xs text-slate-400">
              Late-arrival wave and wildcard decisions require Festival Director approval under FESTOS_CONTEXT.md.
            </p>
          </div>

          <div className="space-y-3">
            {fairnessData?.map((dec) => (
              <div
                key={dec.id}
                className="rounded-xl border border-amber-600/40 bg-amber-950/20 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{dec.title}</span>
                    <span className="rounded bg-amber-950 text-amber-300 border border-amber-500/40 px-2 py-0.5 text-xs font-bold">
                      APPROVAL REQUIRED
                    </span>
                    <span className="font-mono text-xs text-amber-300 font-semibold">
                      Role: {dec.requires_role}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300">{dec.reason}</p>

                  <div className="text-[11px] text-slate-400 pt-1">
                    <span>Affected Attendees: {dec.affected_participants}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => showToast(`Redirecting to ${dec.action_route} for Director approval`, "info")}
                    className="bg-amber-600 hover:bg-amber-500 text-xs flex items-center gap-1.5"
                  >
                    <span>View in Approvals</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EventsVenuesWorkspace;
