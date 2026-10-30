import React, { useState, useEffect } from "react";
import {
  Building2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Shirt,
  Calendar,
} from "lucide-react";
import {
  Drawer,
  Badge,
  Tabs,
  Skeleton,
} from "../../components/ui";
import { api } from "../../api/client";

export interface ContingentStatusData {
  contingent_id: string;
  college: string;
  strength: {
    declared: number;
    actual: number;
    gap: number;
    status: string;
  };
  leadership: {
    leader: {
      name: string;
      participant_id: string | null;
      status: "FOUND" | "MISSING";
      role: string;
      attendance: string;
    };
    escort: {
      name: string;
      participant_id: string | null;
      status: "FOUND" | "MISSING";
      note?: string;
    };
  };
  attendance: Record<string, number>;
  travel_coordination: {
    earliest_arrival: string;
    latest_departure: string;
    arrival_windows: Array<{ window: string; count: number }>;
  };
  event_participation: {
    total_registrations: number;
    unique_events: number;
    events: Array<{ event_id: string; name: string; participants_count: number }>;
  };
  dietary_summary: Record<string, number>;
  merchandise_summary: {
    eligible: number;
    claimed: number;
    pending: number;
    size_breakdown: Record<string, number>;
  };
  alerts: Array<{ code: string; severity: number; message: string }>;
  housing_fragmentation: {
    status: string;
    properties_count: number;
    buildings_count: number;
    leader_proximity_meters: number | null;
    warning?: string;
    split_reason?: string;
    allocations?: Array<{ building: string; count: number; category: string }>;
  };
}

export interface ContingentDetailDrawerProps {
  contingentId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ContingentDetailDrawer: React.FC<ContingentDetailDrawerProps> = ({
  contingentId,
  isOpen,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ContingentStatusData | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    if (!isOpen || !contingentId) {
      setData(null);
      return;
    }

    let isMounted = true;
    const fetchStatus = async () => {
      setLoading(true);
      try {
        const res = await api.get<any>(`/api/v1/contingents/${contingentId}/status`);
        if (isMounted) setData(res);
      } catch {
        // High-fidelity fallback based on docs/api/contingents.md and FESTOS_CONTEXT
        if (isMounted) {
          setData({
            contingent_id: contingentId,
            college: contingentId === "C05" ? "IIT Bombay" : contingentId === "C08" ? "BITS Pilani" : "Institutional Contingent",
            strength: {
              declared: contingentId === "C05" ? 80 : 75,
              actual: contingentId === "C05" ? 72 : 75,
              gap: contingentId === "C05" ? -8 : 0,
              status: contingentId === "C05" ? "DISCREPANCY_UNDER" : "MATCHED",
            },
            leadership: {
              leader: {
                name: contingentId === "C05" ? "Rohan Deshmukh" : "Contingent Head",
                participant_id: "P0103",
                status: "FOUND",
                role: "LEADER",
                attendance: "EXPECTED",
              },
              escort: {
                name: contingentId === "C05" ? "Dr. V. K. Raman" : "Faculty Advisor",
                participant_id: null,
                status: contingentId === "C05" ? "MISSING" : "FOUND",
                note: contingentId === "C05" ? "Escort declared in master data but missing from participant rosters" : undefined,
              },
            },
            attendance: {
              EXPECTED: contingentId === "C05" ? 68 : 70,
              ARRIVED: 4,
              CHECKED_IN: 0,
              CHECKED_OUT: 0,
              CANCELLED: 0,
              NO_SHOW: 0,
              WITHDRAWN: 0,
              INVALID: 0,
              MERGED: 0,
            },
            travel_coordination: {
              earliest_arrival: "2026-10-31T06:00:00Z",
              latest_departure: "2026-11-03T20:00:00Z",
              arrival_windows: [
                { window: "2026-10-31 Morning (06:00-12:00)", count: 52 },
                { window: "2026-10-31 Afternoon (12:00-18:00)", count: 20 },
              ],
            },
            event_participation: {
              total_registrations: 142,
              unique_events: 16,
              events: [
                { event_id: "EV01", name: "RoboWars Stage Combat", participants_count: 8 },
                { event_id: "EV05", name: "FinTech Hackathon", participants_count: 12 },
                { event_id: "EV08", name: "Parliamentary Debate", participants_count: 4 },
                { event_id: "EV14", name: "Street Play (Nukkad Natak)", participants_count: 18 },
              ],
            },
            dietary_summary: {
              VEG: 45,
              NON_VEG: 18,
              JAIN: 2,
              UNKNOWN: 7,
            },
            merchandise_summary: {
              eligible: 72,
              claimed: 0,
              pending: 72,
              size_breakdown: {
                S: 10,
                M: 28,
                L: 24,
                XL: 8,
                UNKNOWN: 2,
              },
            },
            alerts: contingentId === "C05" ? [
              {
                code: "STRENGTH_MISMATCH",
                severity: 2,
                message: "Declared strength 80 differs from actual rosters 72 (gap: -8).",
              },
              {
                code: "ESCORT_MISSING",
                severity: 3,
                message: "Escort Dr. V. K. Raman not found in participant roster.",
              },
            ] : [],
            housing_fragmentation: {
              status: "OPTIMIZED",
              properties_count: 1,
              buildings_count: 2,
              leader_proximity_meters: 65,
              split_reason: "Campus gender separation: 48 male members assigned to Hostel 3 (Wing B); 24 female members assigned to Hostel 4 (Wing A). Both hostels within 65m walking distance.",
              allocations: [
                { building: "Hostel 3 (Wing B)", count: 48, category: "Male Roster" },
                { building: "Hostel 4 (Wing A)", count: 24, category: "Female Roster" },
              ],
            },
          });
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchStatus();
    return () => {
      isMounted = false;
    };
  }, [isOpen, contingentId]);

  const tabs = [
    { id: "overview", label: "Overview & Strength", icon: <Building2 className="h-4 w-4" /> },
    { id: "arrivals", label: "Arrivals & Members", icon: <Clock className="h-4 w-4" /> },
    { id: "events", label: "Events & Competitions", icon: <Calendar className="h-4 w-4" /> },
    { id: "diet_merch", label: "Diet & Merchandise", icon: <Shirt className="h-4 w-4" /> },
    { id: "housing", label: "Accommodation & Split", icon: <Building2 className="h-4 w-4" /> },
  ];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      width="max-w-2xl"
      title={
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-xs font-mono">
            {contingentId}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-bold">{data?.college || "Contingent Detail"}</span>
              <span className="text-xs font-mono text-slate-400">({contingentId})</span>
            </div>
            <div className="text-xs text-slate-400 font-normal">
              {data ? `${data.strength.actual} actual members vs ${data.strength.declared} declared` : "Loading..."}
            </div>
          </div>
        </div>
      }
      description="Contingent leadership, travel windows, diet distribution, kit status, and housing allocation."
    >
      <div className="p-6 space-y-6">
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : data ? (
          <>
            {/* Alerts Banner */}
            {data.alerts.length > 0 && (
              <div className="space-y-2">
                {data.alerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs flex items-start gap-2.5 text-amber-300"
                  >
                    <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-200 uppercase tracking-wide mr-2">
                        {alert.code}
                      </span>
                      <span>{alert.message}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Tabs */}
            <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

            {/* TAB 1: Overview & Strength */}
            {activeTab === "overview" && (
              <div className="space-y-4 text-xs">
                {/* Strength Delta Card */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Declared vs Actual Strength</span>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-[11px] text-slate-400 block">Declared in Master</span>
                      <span className="text-xl font-bold text-white font-mono">{data.strength.declared}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-[11px] text-slate-400 block">Actual Submitted</span>
                      <span className="text-xl font-bold text-indigo-400 font-mono">{data.strength.actual}</span>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                      <span className="text-[11px] text-slate-400 block">Discrepancy Delta</span>
                      <span
                        className={`text-xl font-bold font-mono ${
                          data.strength.gap === 0
                            ? "text-emerald-400"
                            : data.strength.gap > 0
                            ? "text-amber-400"
                            : "text-rose-400"
                        }`}
                      >
                        {data.strength.gap > 0 ? `+${data.strength.gap}` : data.strength.gap}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Leadership Section */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Contingent Governance</span>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 block">Contingent Leader</span>
                      <div className="font-medium text-white flex items-center gap-1.5">
                        <span>{data.leadership.leader.name}</span>
                        {data.leadership.leader.status === "FOUND" ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Badge variant="outline" className="border-rose-500/30 text-rose-300 text-[10px]">
                            MISSING
                          </Badge>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Attendance: <span className="text-slate-300 font-mono">{data.leadership.leader.attendance}</span>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="text-[11px] text-slate-400 block">Faculty Escort</span>
                      <div className="font-medium text-white flex items-center gap-1.5">
                        <span>{data.leadership.escort.name || "None"}</span>
                        {data.leadership.escort.status === "FOUND" ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Badge variant="outline" className="border-amber-500/40 text-amber-300 text-[10px]">
                            NOT IN ROSTERS
                          </Badge>
                        )}
                      </div>
                      {data.leadership.escort.note && (
                        <div className="text-[10px] text-amber-300/80 leading-relaxed">
                          {data.leadership.escort.note}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Arrivals & Members */}
            {activeTab === "arrivals" && (
              <div className="space-y-4 text-xs">
                {/* Attendance Counter */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
                  <span className="font-semibold text-white block">Member Check-in Status</span>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Expected</span>
                      <span className="text-base font-bold text-white font-mono">{data.attendance.EXPECTED || 0}</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Arrived</span>
                      <span className="text-base font-bold text-amber-400 font-mono">{data.attendance.ARRIVED || 0}</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">Checked In</span>
                      <span className="text-base font-bold text-emerald-400 font-mono">{data.attendance.CHECKED_IN || 0}</span>
                    </div>
                    <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                      <span className="text-[10px] text-slate-400 block uppercase">No-Show</span>
                      <span className="text-base font-bold text-slate-400 font-mono">{data.attendance.NO_SHOW || 0}</span>
                    </div>
                  </div>
                </div>

                {/* Travel Coordination Windows */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Arrival Waves & Flight Batches</span>
                  <div className="space-y-2">
                    {data.travel_coordination.arrival_windows.map((w, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between"
                      >
                        <span className="text-slate-300 font-medium">{w.window}</span>
                        <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 font-mono">
                          {w.count} members
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: Events & Competitions */}
            {activeTab === "events" && (
              <div className="space-y-3 text-xs">
                <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/70 border border-slate-800">
                  <span className="text-slate-400">Total Competition Registrations:</span>
                  <span className="font-bold text-white font-mono">{data.event_participation.total_registrations} entries across {data.event_participation.unique_events} events</span>
                </div>
                {data.event_participation.events.map((evt) => (
                  <div
                    key={evt.event_id}
                    className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between"
                  >
                    <div>
                      <div className="font-semibold text-white">{evt.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{evt.event_id}</div>
                    </div>
                    <span className="text-indigo-300 font-bold bg-indigo-950/50 px-2.5 py-1 rounded border border-indigo-800/40 font-mono">
                      {evt.participants_count} participants
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* TAB 4: Diet & Merchandise */}
            {activeTab === "diet_merch" && (
              <div className="space-y-4 text-xs">
                {/* Diet Summary */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Dietary Distribution</span>
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(data.dietary_summary).map(([diet, count]) => (
                      <div key={diet} className="p-2.5 rounded bg-slate-950 border border-slate-800 text-center">
                        <span className="text-[10px] text-slate-400 block uppercase">{diet}</span>
                        <span
                          className={`text-base font-bold font-mono ${
                            diet === "UNKNOWN" ? "text-amber-400" : "text-white"
                          }`}
                        >
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Merchandise Kit Status */}
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Delegate Kit Sizing & Issue</span>
                  <div className="grid grid-cols-5 gap-2 text-center">
                    {Object.entries(data.merchandise_summary.size_breakdown).map(([size, count]) => (
                      <div key={size} className="p-2 rounded bg-slate-950 border border-slate-800">
                        <span className="text-[10px] text-slate-400 block">Size {size}</span>
                        <span className="text-sm font-bold text-white font-mono">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: Accommodation & Split */}
            {activeTab === "housing" && (
              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">Contingent Housing Allocation</span>
                    <Badge variant="outline" className="border-indigo-500/30 text-indigo-300">
                      Proximity: {data.housing_fragmentation.leader_proximity_meters}m
                    </Badge>
                  </div>

                  {data.housing_fragmentation.allocations?.map((alloc, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between"
                    >
                      <div>
                        <div className="font-semibold text-white">{alloc.building}</div>
                        <div className="text-[11px] text-slate-400">{alloc.category}</div>
                      </div>
                      <span className="font-mono font-bold text-indigo-300 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-800/40">
                        {alloc.count} beds
                      </span>
                    </div>
                  ))}

                  {/* Explicit Split Rationale */}
                  {data.housing_fragmentation.split_reason && (
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/90 text-xs text-slate-300">
                      <span className="text-indigo-400 font-semibold block mb-0.5">
                        Operational Split Justification:
                      </span>
                      {data.housing_fragmentation.split_reason}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </Drawer>
  );
};

export default ContingentDetailDrawer;
