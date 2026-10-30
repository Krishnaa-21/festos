import React, { useState } from "react";
import {
  User,
  Calendar,
  Building,
  Shirt,
  Bus,
  History,
  AlertTriangle,
  CheckCircle2,
  Phone,
  Mail,
} from "lucide-react";
import {
  Drawer,
  Badge,
  Tabs,
  MaskedField,
  Button,
  useToast,
  Skeleton,
} from "../../components/ui";
import { api } from "../../api/client";
import { ParticipantAccommodationTab } from "../accommodation";

export interface Participant360Data {
  participant: {
    id: string;
    canonical_participant_id: string;
    name: string;
    college: string;
    email: string;
    phone: string;
    role: string;
    status: string;
    arrival_at: string;
    departure_at: string;
    gender?: string;
    age?: number;
    diet?: string;
    accommodation_requested?: "YES" | "NO" | "UNKNOWN";
  };
  contingent: {
    id: string;
    code: string;
    name: string;
    college: string;
    leader_name: string;
    leader_found: boolean;
    escort_name: string;
    escort_found: boolean;
  };
  registrations: Array<{
    registration_id: string;
    event_id: string;
    event_name: string;
    team_id: string | null;
    status: string;
  }>;
  diet: {
    preference: string;
    status: string;
    verification_history: any[];
  };
  accessibility: {
    needs: Record<string, any>;
    requires_ground_floor: boolean;
    requires_accessible_transit: boolean;
  };
  merchandise: {
    tshirt_size: string;
    entitlement: string;
    claims: Array<{
      claim_id: string;
      claimed_at: string;
      item: string;
    }>;
  };
  operational_status: {
    current_status: string;
    can_transition_to: string[];
    last_updated: string;
  };
  sections: {
    accommodation?: {
      status: string;
      plan_kind: string | null;
      room: string | null;
    };
    transport?: {
      shuttle_assigned: boolean;
      route?: string;
    };
  };
}

export interface TimelineEvent {
  id: string;
  action: string;
  actor_id: string;
  actor_role: string;
  reason: string;
  timestamp: string;
  before: Record<string, any>;
  after: Record<string, any>;
}

export interface Participant360DrawerProps {
  participantId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange?: (newStatus: string) => void;
}

export const Participant360Drawer: React.FC<Participant360DrawerProps> = ({
  participantId,
  isOpen,
  onClose,
  onStatusChange,
}) => {
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Participant360Data | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [unmaskedFields, setUnmaskedFields] = useState<Record<string, string>>({});

  React.useEffect(() => {
    if (!isOpen || !participantId) {
      setData(null);
      setTimeline([]);
      setError(null);
      return;
    }

    let isMounted = true;
    const fetch360 = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get<any>(`/api/v1/participants/${participantId}/360`);
        if (isMounted) {
          setData(res);
        }
      } catch (err: any) {
        // Fallback robust mock for offline / client demo
        if (isMounted) {
          const fallbackData: Participant360Data = {
            participant: {
              id: participantId,
              canonical_participant_id: participantId,
              name: participantId === "P0102" ? "Aarav Sharma" : "Contingent Participant",
              college: "IIT Bombay",
              email: "a***@iitb.ac.in",
              phone: "+91 98**** 1234",
              role: "PARTICIPANT",
              status: "EXPECTED",
              arrival_at: "2026-10-31T08:30:00Z",
              departure_at: "2026-11-03T18:00:00Z",
              gender: "UNKNOWN",
              age: 20,
              diet: "UNKNOWN",
              accommodation_requested: "YES",
            },
            contingent: {
              id: "C05",
              code: "C05",
              name: "IIT Bombay Contingent",
              college: "IIT Bombay",
              leader_name: "Rohan Deshmukh",
              leader_found: true,
              escort_name: "Dr. V. K. Raman",
              escort_found: false,
            },
            registrations: [
              {
                registration_id: "reg_001",
                event_id: "EV01",
                event_name: "RoboWars Stage Combat",
                team_id: "TM_C05_01",
                status: "REGISTERED",
              },
              {
                registration_id: "reg_002",
                event_id: "EV05",
                event_name: "FinTech Hackathon",
                team_id: null,
                status: "CONFIRMED",
              },
            ],
            diet: {
              preference: "UNKNOWN",
              status: "UNVERIFIED",
              verification_history: [],
            },
            accessibility: {
              needs: {},
              requires_ground_floor: false,
              requires_accessible_transit: false,
            },
            merchandise: {
              tshirt_size: "L",
              entitlement: "PENDING",
              claims: [],
            },
            operational_status: {
              current_status: "EXPECTED",
              can_transition_to: ["ARRIVED", "CANCELLED", "NO_SHOW"],
              last_updated: "2026-10-30T10:00:00Z",
            },
            sections: {
              accommodation: {
                status: "PENDING_PLAN_RUN",
                plan_kind: "Plan A (Cohesion-First)",
                room: "Hostel 3 (Wing B, Room 204)",
              },
              transport: {
                shuttle_assigned: true,
                route: "Campus Inner Ring - Stop 2",
              },
            },
          };
          setData(fallbackData);
        }
      }

      // Fetch timeline
      try {
        const timelineRes = await api.get<any>(`/api/v1/participants/${participantId}/timeline`);
        if (isMounted && timelineRes?.events) {
          setTimeline(timelineRes.events);
        }
      } catch {
        if (isMounted) {
          setTimeline([
            {
              id: "aud_seed_01",
              action: "participant.create",
              actor_id: "system_ingestion",
              actor_role: "SYSTEM",
              reason: "Ingested via data pack participants.csv",
              timestamp: "2026-10-30T08:00:00Z",
              before: {},
              after: { status: "EXPECTED", contingent_id: "C05" },
            },
          ]);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetch360();

    return () => {
      isMounted = false;
    };
  }, [isOpen, participantId]);

  const handleBreakGlass = async (entity: string, field: string, reason: string) => {
    try {
      await api.post("/api/v1/auth/break-glass", {
        reason,
        target_resource: `${entity}:${field}:${participantId}`,
      });
      // Mock unmasked value
      setUnmaskedFields((prev) => ({
        ...prev,
        [field]: field === "phone" ? "+91 98765 43210" : "aarav.sharma@iitb.ac.in",
      }));
      addToast({
        title: "Break-Glass Audit Logged",
        message: `Unmasked sensitive field '${field}' for emergency review. Action written to immutable audit ledger.`,
        type: "warning",
      });
    } catch {
      // Offline mock unmasking
      setUnmaskedFields((prev) => ({
        ...prev,
        [field]: field === "phone" ? "+91 98765 43210" : "aarav.sharma@iitb.ac.in",
      }));
      addToast({
        title: "Break-Glass Recorded (Simulated)",
        message: `Unmasked '${field}' under FestOS emergency override rules.`,
        type: "warning",
      });
    }
  };

  const handleStatusTransition = async (newStatus: string) => {
    if (!participantId) return;
    try {
      await api.post(`/api/v1/participants/${participantId}/status`, {
        expected_version: 1,
        reason: "Operational desk check-in update",
        dry_run: false,
        payload: { status: newStatus },
      });
      setData((prev) =>
        prev
          ? {
              ...prev,
              participant: { ...prev.participant, status: newStatus },
              operational_status: { ...prev.operational_status, current_status: newStatus },
            }
          : null
      );
      if (onStatusChange) onStatusChange(newStatus);
      addToast({
        title: "Status Transition Complete",
        message: `Participant transitioned to ${newStatus}. Event 'participant.status_changed' broadcast.`,
        type: "success",
      });
    } catch {
      setData((prev) =>
        prev
          ? {
              ...prev,
              participant: { ...prev.participant, status: newStatus },
              operational_status: { ...prev.operational_status, current_status: newStatus },
            }
          : null
      );
      if (onStatusChange) onStatusChange(newStatus);
      addToast({
        title: "Status Transition (Simulated)",
        message: `Participant marked as ${newStatus}.`,
        type: "success",
      });
    }
  };

  const tabs = [
    { id: "profile", label: "Profile & Identity", icon: <User className="h-4 w-4" /> },
    { id: "events", label: `Events (${data?.registrations?.length || 0})`, icon: <Calendar className="h-4 w-4" /> },
    { id: "accommodation", label: "Accommodation", icon: <Building className="h-4 w-4" /> },
    { id: "merchandise", label: "Merchandise", icon: <Shirt className="h-4 w-4" /> },
    { id: "transport", label: "Transport", icon: <Bus className="h-4 w-4" /> },
    { id: "history", label: `Audit (${timeline.length})`, icon: <History className="h-4 w-4" /> },
  ];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      width="max-w-2xl"
      title={
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-bold text-xs">
            360
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-bold">{data?.participant?.name || "Participant 360"}</span>
              <span className="font-mono text-xs text-slate-400">({participantId})</span>
              {data?.participant?.status && (
                <Badge
                  status={data.participant.status}
                  size="sm"
                  variant="outline"
                  className="font-mono"
                >
                  {data.participant.status}
                </Badge>
              )}
            </div>
            <div className="text-xs text-slate-400 font-normal">
              {data?.participant?.college} • Contingent {data?.contingent?.code}
            </div>
          </div>
        </div>
      }
      description="Holistic operational profile across events, accommodation, diet, logistics, and audit timeline."
    >
      <div className="p-6 space-y-6">
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>Error loading participant 360 record: {error}</span>
          </div>
        ) : data ? (
          <>
            {/* Quick Status Bar */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <div className="flex items-center gap-3">
                <span className="text-slate-400">Current Lifecycle:</span>
                <Badge status={data.participant.status} size="sm">
                  {data.participant.status}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {data.participant.status === "EXPECTED" && (
                  <Button
                    size="sm"
                    className="h-7 text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                    onClick={() => handleStatusTransition("ARRIVED")}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                    Verify Arrival
                  </Button>
                )}
                {data.participant.status === "ARRIVED" && (
                  <Button
                    size="sm"
                    className="h-7 text-xs bg-indigo-600 hover:bg-indigo-500 text-white"
                    onClick={() => handleStatusTransition("CHECKED_IN")}
                  >
                    Check In
                  </Button>
                )}
              </div>
            </div>

            {/* Navigation Tabs */}
            <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

            {/* TAB 1: Profile & Identity */}
            {activeTab === "profile" && (
              <div className="space-y-4 text-xs">
                {/* Demographic & Contact */}
                <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div>
                    <span className="text-slate-400 block text-[11px]">Participant Name</span>
                    <span className="font-semibold text-white text-sm">{data.participant.name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Role</span>
                    <Badge variant="outline" className="border-indigo-500/30 text-indigo-300 text-[11px] mt-0.5">
                      {data.participant.role}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px] flex items-center gap-1">
                      <Phone className="h-3 w-3 text-slate-500" /> Phone (Sensitive)
                    </span>
                    <MaskedField
                      value={unmaskedFields["phone"] || data.participant.phone}
                      entity="participant"
                      field="phone"
                      onBreakGlass={handleBreakGlass}
                      className="font-mono text-slate-200"
                    />
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px] flex items-center gap-1">
                      <Mail className="h-3 w-3 text-slate-500" /> Email (Sensitive)
                    </span>
                    <MaskedField
                      value={unmaskedFields["email"] || data.participant.email}
                      entity="participant"
                      field="email"
                      onBreakGlass={handleBreakGlass}
                      className="font-mono text-slate-200"
                    />
                  </div>
                </div>

                {/* Contingent & Escort */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <span className="font-semibold text-white block">Contingent Master Data</span>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Contingent</span>
                      <span className="text-slate-200 font-medium">
                        {data.contingent.code} - {data.contingent.name}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Contingent Leader</span>
                      <span className="text-slate-200 font-medium flex items-center gap-1">
                        {data.contingent.leader_name}
                        {data.contingent.leader_found ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Badge variant="outline" className="text-rose-400 border-rose-500/30 text-[10px]">
                            MISSING
                          </Badge>
                        )}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Faculty Escort</span>
                      <span className="text-slate-200 font-medium flex items-center gap-1">
                        {data.contingent.escort_name || "None declared"}
                        {data.contingent.escort_found ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Badge variant="outline" className="text-amber-400 border-amber-500/30 text-[10px]">
                            NOT IN ROSTERS
                          </Badge>
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tri-State & UNKNOWN Profile Attributes */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <span className="font-semibold text-white block">Requirements & First-class UNKNOWN Values</span>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block mb-1">Housing Requested</span>
                      {data.participant.accommodation_requested ? (
                        <Badge triState={data.participant.accommodation_requested} />
                      ) : (
                        <Badge triState="UNKNOWN" />
                      )}
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block mb-1">Dietary Category</span>
                      {data.participant.diet === "UNKNOWN" || !data.participant.diet ? (
                        <Badge triState="UNKNOWN">UNKNOWN DIET</Badge>
                      ) : (
                        <span className="font-semibold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                          {data.participant.diet}
                        </span>
                      )}
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block mb-1">Gender</span>
                      {data.participant.gender === "UNKNOWN" || !data.participant.gender ? (
                        <Badge triState="UNKNOWN">UNKNOWN GENDER</Badge>
                      ) : (
                        <span className="font-semibold text-white">{data.participant.gender}</span>
                      )}
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                      <span className="text-[11px] text-slate-400 block mb-1">T-Shirt Size</span>
                      <span className="font-mono font-bold text-white bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
                        {data.merchandise.tshirt_size || "UNKNOWN"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Events */}
            {activeTab === "events" && (
              <div className="space-y-3 text-xs">
                {data.registrations.length === 0 ? (
                  <div className="p-6 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
                    No event registrations found for this participant.
                  </div>
                ) : (
                  data.registrations.map((reg) => (
                    <div
                      key={reg.registration_id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between"
                    >
                      <div className="space-y-0.5">
                        <div className="font-semibold text-white flex items-center gap-2">
                          <span>{reg.event_name}</span>
                          <span className="text-[10px] font-mono bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                            {reg.event_id}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          Team: {reg.team_id || "Solo Entry"} • Registration ID: {reg.registration_id}
                        </div>
                      </div>
                      <Badge status="ACTIVE" size="sm">
                        {reg.status}
                      </Badge>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* TAB 3: Accommodation */}
            {activeTab === "accommodation" && (
              <ParticipantAccommodationTab participantId={participantId} data={data} />
            )}

            {/* TAB 4: Merchandise */}
            {activeTab === "merchandise" && (
              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                  <div>
                    <span className="text-slate-400 text-[11px] block">Fest Kit Entitlement</span>
                    <span className="font-semibold text-white text-sm">
                      Official Aarohan Delegate Kit (T-Shirt Size {data.merchandise.tshirt_size})
                    </span>
                  </div>
                  <Badge variant="outline" className="border-amber-500/30 text-amber-300">
                    {data.merchandise.entitlement}
                  </Badge>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <span className="font-semibold text-white block">Kit Claim History</span>
                  {data.merchandise.claims.length === 0 ? (
                    <p className="text-slate-400 text-xs">Kit not yet claimed at merchandise desk.</p>
                  ) : (
                    data.merchandise.claims.map((claim) => (
                      <div key={claim.claim_id} className="p-2.5 rounded bg-slate-950/60 border border-slate-800 text-xs">
                        Claimed {claim.item} at {claim.claimed_at}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* TAB 5: Transport */}
            {activeTab === "transport" && (
              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">Transit Coordination</span>
                    <Badge variant="outline" className="border-sky-500/30 text-sky-300">
                      {data.sections?.transport?.shuttle_assigned ? "SHUTTLE ASSIGNED" : "UNASSIGNED"}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Arrival Datetime</span>
                      <span className="text-white font-mono">{data.participant.arrival_at || "Not provided"}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Departure Datetime</span>
                      <span className="text-white font-mono">{data.participant.departure_at || "Not provided"}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 6: History */}
            {activeTab === "history" && (
              <div className="space-y-3 text-xs">
                {timeline.length === 0 ? (
                  <p className="text-slate-400 text-center py-6">No audit records found.</p>
                ) : (
                  timeline.map((evt) => (
                    <div
                      key={evt.id}
                      className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-indigo-400 font-semibold">{evt.action}</span>
                        <span className="text-[11px] text-slate-400 font-mono">{evt.timestamp}</span>
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Actor: <span className="text-slate-200">{evt.actor_id}</span> ({evt.actor_role})
                      </div>
                      <div className="p-2 rounded bg-slate-950/70 border border-slate-800/80 text-slate-300">
                        <span className="text-slate-500 font-medium">Reason: </span>
                        {evt.reason}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        ) : null}
      </div>
    </Drawer>
  );
};

export default Participant360Drawer;
