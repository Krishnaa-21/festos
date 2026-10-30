import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  TransportAssumptions,
  ShuttlePlanSlot,
  NightSafetyParticipant,
  GuardianQueueEntry,
  SafetyCoverageSummary,
  TransportAlert,
} from "./types";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ConfirmWithReason } from "../../components/ui/ConfirmWithReason";
import { useToast } from "../../components/ui/Toast";
import {
  Truck,
  Shield,
  Moon,
  AlertTriangle,
  CheckCircle2,
  Edit3,
  UserCheck,
  Building,
  Phone,
  ShieldAlert,
} from "lucide-react";

export const TransportSafetyWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<"shuttles" | "night_safety" | "guardians">("shuttles");
  const [isEditAssumptionsOpen, setIsEditAssumptionsOpen] = useState(false);
  const [editedAssumptions, setEditedAssumptions] = useState<Partial<TransportAssumptions>>({});
  const [assumptionReason, setAssumptionReason] = useState("");

  const [selectedGuardianForApproval, setSelectedGuardianForApproval] = useState<GuardianQueueEntry | null>(null);
  const [isGuardianConfirmOpen, setIsGuardianConfirmOpen] = useState(false);

  // 1. Fetch Transport Assumptions (Marked ASSUMED)
  const { data: assumptionsData, refetch: refetchAssumptions } = useQuery<TransportAssumptions>({
    queryKey: ["transport_assumptions"],
    queryFn: async () => {
      const res = await api.get<TransportAssumptions>("/api/v1/transport/assumptions");
      return res;
    },
  });

  // 2. Fetch Shuttle Plan
  const { data: shuttlePlanData } = useQuery<{
    slots: ShuttlePlanSlot[];
    totalDemand: number;
    totalCapacity: number;
    netDeficit: number;
  }>({
    queryKey: ["shuttle_plan"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/transport/shuttles/plan");
      return res;
    },
  });

  // 3. Fetch Night Safety Roster
  const { data: nightRosterData, refetch: refetchNightRoster } = useQuery<{
    items: NightSafetyParticipant[];
    total: number;
    unverified_count: number;
  }>({
    queryKey: ["night_safety_roster"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/transport/safety/night-roster");
      return res;
    },
  });

  // 4. Fetch Guardians Queue
  const { data: guardiansData, refetch: refetchGuardians } = useQuery<{
    items: GuardianQueueEntry[];
    total: number;
    pending_count: number;
  }>({
    queryKey: ["guardians_queue"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/transport/guardians/queue");
      return res;
    },
  });

  // 5. Fetch Safety Coverage Summary (KPIs)
  const { data: coverageSummary } = useQuery<SafetyCoverageSummary>({
    queryKey: ["transport_coverage_summary"],
    queryFn: async () => {
      const res = await api.get<SafetyCoverageSummary>("/api/v1/transport/coverage/summary");
      return res;
    },
  });

  // 6. Fetch Transport Alerts
  const { data: alertsData, refetch: refetchAlerts } = useQuery<{ items: TransportAlert[]; total: number }>({
    queryKey: ["transport_alerts"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/transport/alerts");
      return res;
    },
  });

  // Update Assumptions Mutation
  const updateAssumptionsMutation = useMutation({
    mutationFn: async (payload: { assumptions: Partial<TransportAssumptions>; reason: string }) => {
      return api.patch("/api/v1/transport/assumptions", {
        payload: payload.assumptions,
        reason: payload.reason,
      });
    },
    onSuccess: () => {
      refetchAssumptions();
      queryClient.invalidateQueries({ queryKey: ["shuttle_plan"] });
      queryClient.invalidateQueries({ queryKey: ["transport_coverage_summary"] });
      addToast({
        title: "Assumptions Updated",
        message: "Transport fleet capacity recalculated with recorded reason.",
        type: "success",
      });
      setIsEditAssumptionsOpen(false);
      setAssumptionReason("");
    },
  });

  // Toggle Verification for Night Escort
  const toggleVerifyMutation = useMutation({
    mutationFn: async (participantId: string) => {
      return api.post("/api/v1/transport/safety/verify", {
        participant_id: participantId,
      });
    },
    onSuccess: () => {
      refetchNightRoster();
      queryClient.invalidateQueries({ queryKey: ["transport_coverage_summary"] });
      addToast({
        title: "Escort Verification Updated",
        message: "Night journey security status recorded.",
        type: "info",
      });
    },
  });

  // Guardian Queue Approval Mutation
  const approveGuardianMutation = useMutation({
    mutationFn: async ({ id, action, reason }: { id: string; action: "APPROVE" | "REJECT"; reason: string }) => {
      return api.post(`/api/v1/transport/guardians/${id}/approve`, {
        action,
        reason,
      });
    },
    onSuccess: () => {
      refetchGuardians();
      queryClient.invalidateQueries({ queryKey: ["transport_coverage_summary"] });
      addToast({
        title: "Guardian Authorization Recorded",
        message: "Minor accommodation permission updated.",
        type: "success",
      });
      setIsGuardianConfirmOpen(false);
      setSelectedGuardianForApproval(null);
    },
  });

  // Resolve Transport Alert
  const resolveAlertMutation = useMutation({
    mutationFn: async (alertId: string) => {
      return api.post(`/api/v1/transport/alerts/${alertId}/resolve`);
    },
    onSuccess: () => {
      refetchAlerts();
      queryClient.invalidateQueries({ queryKey: ["shuttle_plan"] });
      addToast({
        title: "Action Dispatched",
        message: "Emergency transport adjustment executed.",
        type: "success",
      });
    },
  });

  const assumptions = assumptionsData || {
    shuttle_capacity_seats: 12,
    shuttle_vehicle_count: 3,
    shuttle_travel_min: 25,
    transport_hours: "06:00-22:00",
    cleaning_buffer_minutes: 180,
    late_night_start: "22:00",
    late_night_end: "06:00",
    minor_age_threshold: 18,
  };

  const shuttleSlots = shuttlePlanData?.slots || [];
  const nightRoster = nightRosterData?.items || [];
  const guardians = guardiansData?.items || [];
  const alerts = alertsData?.items || [];

  return (
    <div className="space-y-6" data-testid="transport-safety-workspace">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400">
              <Truck className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Transportation & Night Safety</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Duty-of-care command centre: heuristic shuttle capacity vs demand, late-night escort verification, and minor guardian approvals.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {alerts.filter((a) => !a.isResolved).length > 0 && (
            <Badge status="REJECTED" className="animate-pulse">
              {alerts.filter((a) => !a.isResolved).length} URGENT ALERTS
            </Badge>
          )}
        </div>
      </div>

      {/* ASSUMED Parameter Banner with Edit Links */}
      <div
        className="rounded-xl border border-indigo-500/40 bg-indigo-950/20 p-4 shadow-sm backdrop-blur flex flex-col md:flex-row md:items-center justify-between gap-3"
        data-testid="assumed-parameter-banner"
      >
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Badge status="PENDING" className="font-mono text-[9px]">
              ASSUMED PARAMETERS
            </Badge>
            <span className="text-xs font-bold text-white">Transportation Planning Heuristics (Section 10)</span>
          </div>
          <p className="text-xs text-slate-300">
            Shuttle schedule is derived from participant arrival timestamps and external property distances. Parameters
            are heuristic approximations.
          </p>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 font-mono pt-1">
            <span>Capacity: <strong className="text-white">{assumptions.shuttle_capacity_seats} seats</strong></span>
            <span>•</span>
            <span>Fleet: <strong className="text-white">{assumptions.shuttle_vehicle_count} vehicles</strong></span>
            <span>•</span>
            <span>Travel Time: <strong className="text-white">{assumptions.shuttle_travel_min} min</strong></span>
            <span>•</span>
            <span>Night Window: <strong className="text-white">{assumptions.late_night_start}-{assumptions.late_night_end}</strong></span>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          className="text-xs shrink-0"
          onClick={() => {
            setEditedAssumptions(assumptions);
            setIsEditAssumptionsOpen(true);
          }}
          data-testid="edit-assumptions-btn"
        >
          <Edit3 className="mr-1.5 h-3.5 w-3.5" /> Edit Parameters
        </Button>
      </div>

      {/* Safety Coverage Tiles (7 KPIs) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5" data-testid="safety-coverage-tiles">
        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Total Transit Pax</span>
          <div className="text-xl font-bold font-mono text-white mt-1">{coverageSummary?.totalRequiringTransport ?? 186}</div>
          <span className="text-[9px] text-slate-500">External Stays</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Confirmed Seats</span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{coverageSummary?.confirmedShuttleCapacity ?? 168}</div>
          <span className="text-[9px] text-emerald-500">Across Runs</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Uncovered Requests</span>
          <div className="text-xl font-bold font-mono text-red-400 mt-1">{coverageSummary?.uncoveredTransportRequests ?? 18}</div>
          <span className="text-[9px] text-red-400">Seat Shortfall</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Night Movements</span>
          <div className="text-xl font-bold font-mono text-amber-400 mt-1">{coverageSummary?.lateNightMovements ?? 24}</div>
          <span className="text-[9px] text-amber-400">22:00 - 06:00</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Minor Approvals</span>
          <div className="text-xl font-bold font-mono text-sky-400 mt-1">{coverageSummary?.minorExternalAccommodations ?? 14}</div>
          <span className="text-[9px] text-sky-400">&lt;18 External</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">Unassigned Escorts</span>
          <div className="text-xl font-bold font-mono text-rose-400 mt-1">{coverageSummary?.unassignedEscorts ?? 5}</div>
          <span className="text-[9px] text-rose-400">Action Needed</span>
        </div>

        <div className="rounded-lg border border-slate-800 bg-[#0E1526] p-3 text-center">
          <span className="text-[10px] font-bold uppercase text-slate-400 block">High-Risk Trips</span>
          <div className="text-xl font-bold font-mono text-purple-400 mt-1">{coverageSummary?.highRiskPropertyTrips ?? 2}</div>
          <span className="text-[9px] text-purple-400">&gt;30 min Travel</span>
        </div>
      </div>

      {/* Plain-Language Transport Alerts */}
      <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-3" data-testid="transport-alerts-section">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Duty-of-Care & Transportation Alerts (Plain Language)
          </h2>
        </div>

        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-lg border p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs transition-all ${
                alert.isResolved
                  ? "border-slate-800 bg-slate-900/40 text-slate-400"
                  : alert.severity === "CRITICAL"
                  ? "border-red-500/50 bg-red-950/20 text-red-200"
                  : "border-amber-500/40 bg-amber-950/20 text-amber-200"
              }`}
              data-testid={`transport-alert-${alert.id}`}
            >
              <div className="flex items-start space-x-3">
                <span className="mt-0.5 shrink-0">
                  {alert.isResolved ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : alert.severity === "CRITICAL" ? (
                    <ShieldAlert className="h-4 w-4 text-red-400" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                  )}
                </span>
                <div>
                  <p className="font-medium text-slate-100 leading-relaxed">{alert.message}</p>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">
                    Triggered by Heuristic Duty-of-Care Watcher
                  </span>
                </div>
              </div>

              <div className="shrink-0 flex items-center space-x-2">
                {alert.isResolved ? (
                  <Badge status="SUCCESS">RESOLVED</Badge>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    className="text-xs"
                    onClick={() => resolveAlertMutation.mutate(alert.id)}
                    data-testid={`alert-action-${alert.id}`}
                  >
                    {alert.suggestedActionLabel}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 text-xs font-bold uppercase tracking-wider">
        <button
          onClick={() => setActiveTab("shuttles")}
          className={`pb-3 border-b-2 transition-all ${
            activeTab === "shuttles"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          data-testid="tab-shuttles"
        >
          Shuttle Demand vs Capacity
        </button>

        <button
          onClick={() => setActiveTab("night_safety")}
          className={`pb-3 border-b-2 transition-all flex items-center space-x-1.5 ${
            activeTab === "night_safety"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          data-testid="tab-night-safety"
        >
          <Moon className="h-3.5 w-3.5" />
          <span>Night-Safety Roster ({nightRoster.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("guardians")}
          className={`pb-3 border-b-2 transition-all flex items-center space-x-1.5 ${
            activeTab === "guardians"
              ? "border-indigo-500 text-white"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
          data-testid="tab-guardians"
        >
          <Shield className="h-3.5 w-3.5" />
          <span>Guardian Approvals ({guardians.filter((g) => g.status === "PENDING_REVIEW").length} Pending)</span>
        </button>
      </div>

      {/* TAB 1: SHUTTLE DEMAND VS CONFIRMED CAPACITY */}
      {activeTab === "shuttles" && (
        <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4" data-testid="shuttles-table-view">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Hourly Shuttle Load vs Confirmed Capacity
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Computed per external property and hourly arrival/departure window.
              </p>
            </div>
            <div className="flex items-center space-x-3 text-xs font-mono">
              <span className="text-slate-400">Total Demand: <strong className="text-white">{shuttlePlanData?.totalDemand ?? 153}</strong></span>
              <span>•</span>
              <span className="text-slate-400">Total Capacity: <strong className="text-emerald-400">{shuttlePlanData?.totalCapacity ?? 96}</strong></span>
              <span>•</span>
              <span className="text-red-400 font-bold">Net Deficit: {shuttlePlanData?.netDeficit ?? -57} seats</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] font-bold uppercase text-slate-500">
                  <th className="py-2.5 px-3">Property Name</th>
                  <th className="py-2.5 px-3">Hour Window</th>
                  <th className="py-2.5 px-3">Passenger Demand</th>
                  <th className="py-2.5 px-3">Vehicles Assigned</th>
                  <th className="py-2.5 px-3">Confirmed Capacity</th>
                  <th className="py-2.5 px-3">Balance / Deficit</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {shuttleSlots.map((slot) => {
                  const isDeficit = slot.status === "DEFICIT";
                  return (
                    <tr key={slot.id} className="hover:bg-slate-900/40 transition-colors" data-testid={`shuttle-row-${slot.id}`}>
                      <td className="py-3 px-3 font-semibold text-white">
                        <div className="flex items-center space-x-1.5">
                          <Building className="h-3.5 w-3.5 text-slate-500" />
                          <span>{slot.propertyName}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono">{slot.hour}</td>
                      <td className="py-3 px-3 font-mono font-bold text-white">{slot.passengerDemand} pax</td>
                      <td className="py-3 px-3 font-mono">{slot.assignedVehicles} vehicles</td>
                      <td className="py-3 px-3 font-mono text-emerald-400">{slot.confirmedCapacity} seats</td>
                      <td className="py-3 px-3 font-mono font-bold">
                        {isDeficit ? (
                          <span className="text-red-400">{slot.deficit} SEATS SHORT</span>
                        ) : (
                          <span className="text-emerald-400">BALANCED</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <Badge status={isDeficit ? "REJECTED" : "SUCCESS"}>
                          {slot.status}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: NIGHT-SAFETY ROSTER WITH ESCORT ASSIGNMENT & VERIFICATION */}
      {activeTab === "night_safety" && (
        <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4" data-testid="night-safety-view">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Night-Safety Movement Roster (22:00 - 06:00)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Every late-night journey requires a designated escort and verification toggle under FestOS duty-of-care policy.
              </p>
            </div>
            <span className="text-xs text-amber-400 font-semibold">
              {nightRoster.filter((n) => !n.isVerified).length} Journeys Unverified
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] font-bold uppercase text-slate-500">
                  <th className="py-2.5 px-3">Participant</th>
                  <th className="py-2.5 px-3">Contingent</th>
                  <th className="py-2.5 px-3">Route (Origin &gt; Dest)</th>
                  <th className="py-2.5 px-3">Travel Time</th>
                  <th className="py-2.5 px-3">Assigned Escort</th>
                  <th className="py-2.5 px-3">Safety Status</th>
                  <th className="py-2.5 px-3 text-right">Verification Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {nightRoster.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-900/40 transition-colors" data-testid={`night-roster-row-${entry.id}`}>
                    <td className="py-3 px-3 font-semibold text-white">
                      <div>{entry.name}</div>
                      <div className="flex items-center space-x-1.5 mt-0.5">
                        <span className="font-mono text-[10px] text-slate-400">{entry.participantId}</span>
                        {entry.isMinor && <Badge status="PENDING" className="text-[9px] py-0 px-1">MINOR</Badge>}
                      </div>
                    </td>
                    <td className="py-3 px-3">{entry.contingentName} ({entry.contingentId})</td>
                    <td className="py-3 px-3">
                      <span className="text-slate-300">{entry.origin}</span>
                      <span className="text-slate-500 mx-1">&rarr;</span>
                      <span className="text-indigo-400 font-medium">{entry.destination}</span>
                    </td>
                    <td className="py-3 px-3 font-mono font-bold text-amber-300">{entry.travelTime}</td>
                    <td className="py-3 px-3">
                      {entry.assignedEscortName ? (
                        <div className="flex items-center space-x-1.5 text-slate-200">
                          <UserCheck className="h-3.5 w-3.5 text-teal-400" />
                          <span>{entry.assignedEscortName}</span>
                        </div>
                      ) : (
                        <span className="text-red-400 font-bold uppercase text-[10px]">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <Badge status={entry.isVerified ? "SUCCESS" : "REJECTED"} data-testid={`verify-status-${entry.id}`}>
                        {entry.isVerified ? "VERIFIED" : "UNVERIFIED"}
                      </Badge>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <Button
                        variant={entry.isVerified ? "ghost" : "primary"}
                        size="sm"
                        className="text-xs h-7"
                        onClick={() => toggleVerifyMutation.mutate(entry.participantId)}
                        data-testid={`toggle-verify-btn-${entry.id}`}
                      >
                        {entry.isVerified ? "Revoke Verification" : "Mark Verified"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: GUARDIAN APPROVAL QUEUE FOR MINORS */}
      {activeTab === "guardians" && (
        <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4" data-testid="guardian-queue-view">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Minor Guardian Authorization Queue
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Participants under 18 housed in external properties require explicit, auditable guardian sign-offs.
              </p>
            </div>
            <span className="text-xs text-sky-400 font-semibold">
              {guardians.filter((g) => g.status === "PENDING_REVIEW").length} Requiring Director Review
            </span>
          </div>

          <div className="space-y-3">
            {guardians.map((entry) => (
              <div
                key={entry.id}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
                data-testid={`guardian-row-${entry.id}`}
              >
                <div className="space-y-1.5 max-w-xl">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-white text-sm">{entry.name}</span>
                    <Badge status="PENDING">Age {entry.age}</Badge>
                    <Badge
                      status={
                        entry.status === "APPROVED"
                          ? "SUCCESS"
                          : entry.status === "REJECTED"
                          ? "REJECTED"
                          : "PENDING"
                      }
                    >
                      {entry.status}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-400">
                    <span>ID: <strong className="text-white font-mono">{entry.participantId}</strong></span>
                    <span>•</span>
                    <span>Contingent: <strong>{entry.contingentName}</strong></span>
                    <span>•</span>
                    <span>External Property: <strong className="text-indigo-400">{entry.externalProperty}</strong></span>
                    <span>•</span>
                    <span>Duration: {entry.stayDuration}</span>
                  </div>

                  <div className="flex items-center space-x-3 text-xs text-slate-400 pt-1">
                    <span>Guardian: <strong className="text-slate-300">{entry.guardianName}</strong></span>
                    <span>•</span>
                    <span className="flex items-center">
                      <Phone className="mr-1 h-3 w-3" />
                      {entry.guardianContact}
                    </span>
                    {entry.escortAssigned && (
                      <>
                        <span>•</span>
                        <span className="text-teal-300">Escort: {entry.escortAssigned}</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {entry.status === "PENDING_REVIEW" ? (
                    <>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => {
                          setSelectedGuardianForApproval(entry);
                          setIsGuardianConfirmOpen(true);
                        }}
                        data-testid={`approve-guardian-btn-${entry.id}`}
                      >
                        Approve with Reason
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() =>
                          approveGuardianMutation.mutate({
                            id: entry.id,
                            action: "REJECT",
                            reason: "Missing signed parental affidavit",
                          })
                        }
                      >
                        Reject
                      </Button>
                    </>
                  ) : (
                    <span className="text-xs text-emerald-400 flex items-center">
                      <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approved by {entry.reviewedBy || "Director"}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Assumptions Modal */}
      <Modal
        isOpen={isEditAssumptionsOpen}
        onClose={() => setIsEditAssumptionsOpen(false)}
        title="Edit ASSUMED Transport Parameters"
        description="FestOS principles: Assumptions are visible, editable, owned and sourced. Changes recalculate vehicle runs."
        size="md"
      >
        <div className="space-y-4 text-xs text-slate-200">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Shuttle Capacity (Seats)</label>
              <input
                type="number"
                value={editedAssumptions.shuttle_capacity_seats ?? 12}
                onChange={(e) =>
                  setEditedAssumptions({ ...editedAssumptions, shuttle_capacity_seats: Number(e.target.value) })
                }
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Fleet Vehicles Count</label>
              <input
                type="number"
                value={editedAssumptions.shuttle_vehicle_count ?? 3}
                onChange={(e) =>
                  setEditedAssumptions({ ...editedAssumptions, shuttle_vehicle_count: Number(e.target.value) })
                }
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Shuttle Travel Min</label>
              <input
                type="number"
                value={editedAssumptions.shuttle_travel_min ?? 25}
                onChange={(e) =>
                  setEditedAssumptions({ ...editedAssumptions, shuttle_travel_min: Number(e.target.value) })
                }
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Cleaning Buffer (Min)</label>
              <input
                type="number"
                value={editedAssumptions.cleaning_buffer_minutes ?? 180}
                onChange={(e) =>
                  setEditedAssumptions({ ...editedAssumptions, cleaning_buffer_minutes: Number(e.target.value) })
                }
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold text-slate-300">
              Operational Rationale for Assumption Change <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={2}
              value={assumptionReason}
              onChange={(e) => setAssumptionReason(e.target.value)}
              placeholder="e.g. Additional 20-seat tempo traveler requisitioned from local vendor..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
            <Button variant="ghost" size="sm" onClick={() => setIsEditAssumptionsOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={!assumptionReason.trim()}
              isLoading={updateAssumptionsMutation.isPending}
              onClick={() =>
                updateAssumptionsMutation.mutate({
                  assumptions: editedAssumptions,
                  reason: assumptionReason.trim(),
                })
              }
            >
              Update Assumptions
            </Button>
          </div>
        </div>
      </Modal>

      {/* Guardian Confirmation Modal */}
      {selectedGuardianForApproval && (
        <ConfirmWithReason
          isOpen={isGuardianConfirmOpen}
          onClose={() => setIsGuardianConfirmOpen(false)}
          onConfirm={(reason) =>
            approveGuardianMutation.mutate({
              id: selectedGuardianForApproval.id,
              action: "APPROVE",
              reason,
            })
          }
          title={`Authorize External Housing for ${selectedGuardianForApproval.name}`}
          description={`Approving minor housing at ${selectedGuardianForApproval.externalProperty}. FestOS requires explicit recording of guardian authorization in the audit ledger.`}
          confirmText="Approve Housing & Log"
          placeholder="State verification details (e.g. Verified signed affidavit from dean and phone confirmation)..."
        />
      )}
    </div>
  );
};

export default TransportSafetyWorkspace;
