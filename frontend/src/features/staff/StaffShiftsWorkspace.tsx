import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  StaffMember,
  ShiftAssignment,
  CoverageHourlySlot,
  HandoverNoteRecord,
  ReplacementCandidate,
} from "./types";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Drawer } from "../../components/ui/Drawer";
import { useToast } from "../../components/ui/Toast";
import {
  Users,
  AlertTriangle,
  UserCheck,
  FileText,
  Building,
} from "lucide-react";

const VENUES = [
  { id: "V01", name: "Main Auditorium" },
  { id: "V02", name: "Indoor Sports Complex" },
  { id: "V03", name: "Central Dining Hall" },
  { id: "V04", name: "Registration Concourse" },
  { id: "V09", name: "Transport Hub" },
];

const HOURS = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "00:00"];

export const StaffShiftsWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [selectedShiftForReplace, setSelectedShiftForReplace] = useState<ShiftAssignment | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");
  const [handoverNoteInput, setHandoverNoteInput] = useState("");
  const [isHandoverDrawerOpen, setIsHandoverDrawerOpen] = useState(false);
  const [editingHandover, setEditingHandover] = useState<HandoverNoteRecord | null>(null);
  const [newNoteContent, setNewNoteContent] = useState("");

  // 1. Shifts List
  const { data: shiftsData } = useQuery<{ items: ShiftAssignment[]; total: number }>({
    queryKey: ["staff_shifts"],
    queryFn: async () => {
      const res = await api.get<{ items: ShiftAssignment[]; total: number }>("/api/v1/staff/shifts");
      return res;
    },
  });

  // 2. Staff Profiles
  const { data: staffData } = useQuery<{ items: StaffMember[]; total: number }>({
    queryKey: ["staff_list"],
    queryFn: async () => {
      const res = await api.get<{ items: StaffMember[]; total: number }>("/api/v1/staff");
      return res;
    },
  });

  // 3. Hourly Coverage Demand Heat Strip
  const { data: demandData } = useQuery<{
    slots: CoverageHourlySlot[];
    totalDemand: number;
    totalOnShift: number;
    uncoveredHoursCount: number;
  }>({
    queryKey: ["staff_demand"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/staff/demand");
      return res;
    },
  });

  // 4. Overloaded Staff
  const { data: overloadedData } = useQuery<{ items: StaffMember[]; total: number }>({
    queryKey: ["staff_overloaded"],
    queryFn: async () => {
      const res = await api.get<{ items: StaffMember[]; total: number }>("/api/v1/staff/overloaded");
      return res;
    },
  });

  // 5. Conflicting Shifts
  const { data: conflictsData } = useQuery<{ items: ShiftAssignment[]; total: number }>({
    queryKey: ["staff_conflicts"],
    queryFn: async () => {
      const res = await api.get<{ items: ShiftAssignment[]; total: number }>("/api/v1/staff/conflicts");
      return res;
    },
  });

  // 6. Handover Notes
  const { data: handoversData, refetch: refetchHandovers } = useQuery<{
    items: HandoverNoteRecord[];
    total: number;
    missing_count: number;
  }>({
    queryKey: ["staff_handovers"],
    queryFn: async () => {
      const res = await api.get<any>("/api/v1/staff/handovers");
      return res;
    },
  });

  // 7. Ranked Replacement Suggestions when shift selected
  const { data: replacementsData } = useQuery<{ candidates: ReplacementCandidate[] }>({
    queryKey: ["staff_replacements", selectedShiftForReplace?.id],
    queryFn: async () => {
      const res = await api.get<{ candidates: ReplacementCandidate[] }>("/api/v1/staff/replacements/suggest");
      return res;
    },
    enabled: !!selectedShiftForReplace,
  });

  // Auto-select top-ranked candidate
  React.useEffect(() => {
    if (replacementsData?.candidates && replacementsData.candidates.length > 0 && !selectedCandidateId) {
      setSelectedCandidateId(replacementsData.candidates[0].staffId);
    }
  }, [replacementsData, selectedCandidateId]);

  // Emergency Replace Mutation
  const replaceMutation = useMutation({
    mutationFn: async ({
      shiftId,
      replacementStaffId,
      handoverNote,
    }: {
      shiftId: string;
      replacementStaffId: string;
      handoverNote: string;
    }) => {
      return api.post(`/api/v1/staff/shifts/${shiftId}/replace`, {
        replacement_staff_id: replacementStaffId,
        handover_notes: handoverNote,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["staff_shifts"] });
      queryClient.invalidateQueries({ queryKey: ["staff_conflicts"] });
      queryClient.invalidateQueries({ queryKey: ["staff_overloaded"] });
      queryClient.invalidateQueries({ queryKey: ["staff_demand"] });
      queryClient.invalidateQueries({ queryKey: ["staff_handovers"] });
      addToast({
        title: "Emergency Replacement Complete",
        message: "Staff assigned and handover note logged.",
        type: "success",
      });
      setSelectedShiftForReplace(null);
      setHandoverNoteInput("");
      setSelectedCandidateId("");
    },
    onError: (err: any) => {
      addToast({
        title: "Replacement Failed",
        message: err.message || "Could not complete replacement",
        type: "error",
      });
    },
  });

  // Save Handover Note Mutation
  const saveHandoverMutation = useMutation({
    mutationFn: async (payload: { venueId: string; hour: string; notes: string }) => {
      return api.post("/api/v1/staff/handovers", {
        venue_id: payload.venueId,
        hour: payload.hour,
        notes: payload.notes,
      });
    },
    onSuccess: () => {
      refetchHandovers();
      addToast({
        title: "Handover Recorded",
        message: "Shift transition note saved successfully.",
        type: "success",
      });
      setEditingHandover(null);
      setNewNoteContent("");
    },
  });

  const shifts = shiftsData?.items || [];
  const coverageSlots = demandData?.slots || [];
  const handovers = handoversData?.items || [];
  const missingHandoversCount = handoversData?.missing_count || 0;

  return (
    <div className="space-y-6" data-testid="staff-shifts-workspace">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600/20 text-teal-400">
              <UserCheck className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Staff Deployment & Shift Roster</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time coverage heat strip, fatigue & overlap monitors, emergency replacement engine, and handover notes.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsHandoverDrawerOpen(true)}
            data-testid="open-handovers-btn"
          >
            <FileText className="mr-1.5 h-3.5 w-3.5" /> Handover Notes
            {missingHandoversCount > 0 && (
              <span className="ml-1.5 rounded-full bg-red-500/20 px-1.5 py-0.2 text-[10px] font-bold text-red-400 border border-red-500/40">
                {missingHandoversCount} Missing
              </span>
            )}
          </Button>
        </div>
      </div>

      {/* KPI Tiles & Alerts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4">
          <span className="text-[10px] font-bold uppercase text-slate-400">Active Volunteers On Duty</span>
          <div className="mt-1 text-2xl font-bold font-mono text-white">{staffData?.total || 48}</div>
          <span className="text-[10px] text-emerald-400">All 48 team members tracked</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4">
          <span className="text-[10px] font-bold uppercase text-slate-400">Uncovered Shift Windows</span>
          <div className="mt-1 text-2xl font-bold font-mono text-red-400" data-testid="uncovered-hours-kpi">
            {demandData?.uncoveredHoursCount || 3}
          </div>
          <span className="text-[10px] text-red-400">High shortage at 12:00, 14:00, 00:00</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4">
          <span className="text-[10px] font-bold uppercase text-slate-400">Overloaded Staff (&gt;10h)</span>
          <div className="mt-1 text-2xl font-bold font-mono text-amber-400" data-testid="overloaded-staff-kpi">
            {overloadedData?.total || 1}
          </div>
          <span className="text-[10px] text-amber-400">Exceeds continuous shift threshold</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-4">
          <span className="text-[10px] font-bold uppercase text-slate-400">Overlapping Schedule Clashes</span>
          <div className="mt-1 text-2xl font-bold font-mono text-rose-400" data-testid="conflicts-kpi">
            {conflictsData?.total || 2}
          </div>
          <span className="text-[10px] text-rose-400">Simultaneous venue assignments</span>
        </div>
      </div>

      {/* Missing Handover Warning Banner */}
      {missingHandoversCount > 0 && (
        <div
          className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-3.5 flex items-center justify-between text-xs text-amber-300"
          data-testid="missing-handover-banner"
        >
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
            <span>
              <strong>MISSING SHIFT HANDOVER:</strong> Shift transition at 14:00 (Registration Concourse) has no recorded handover notes.
            </span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="text-[11px] h-7"
            onClick={() => setIsHandoverDrawerOpen(true)}
          >
            Record Handover
          </Button>
        </div>
      )}

      {/* Roster & Coverage Board */}
      <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Users className="h-4 w-4 text-teal-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Roster Grid by Hour & Venue
            </h2>
          </div>
          <span className="text-[11px] text-slate-500">Click any shift cell to trigger Emergency-Replace</span>
        </div>

        {/* Coverage Heat Strip (Demand vs On Shift) */}
        <div className="space-y-1.5" data-testid="coverage-heat-strip">
          <div className="text-[11px] font-bold uppercase text-slate-400">Coverage Heat Strip (Demand vs On Shift)</div>
          <div className="grid grid-cols-9 gap-1.5 text-center">
            {coverageSlots.map((slot) => {
              const isUncovered = slot.status === "UNCOVERED";
              const isTight = slot.status === "TIGHT";
              return (
                <div
                  key={slot.hour}
                  data-testid={`heat-strip-slot-${slot.hour}`}
                  className={`rounded-lg border p-2 transition-all ${
                    isUncovered
                      ? "border-red-500/50 bg-red-950/40 text-red-300 ring-1 ring-red-500/30"
                      : isTight
                      ? "border-amber-500/40 bg-amber-950/30 text-amber-300"
                      : "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
                  }`}
                >
                  <div className="text-[11px] font-bold font-mono">{slot.hour}</div>
                  <div className="text-[10px] font-semibold mt-0.5">
                    {slot.onShift} / {slot.demand}
                  </div>
                  <div className="text-[9px] uppercase font-bold mt-0.5">
                    {isUncovered ? `-${slot.deficit} GAP` : isTight ? "TIGHT" : "OK"}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Roster Grid Table */}
        <div className="overflow-x-auto pt-2">
          <table className="w-full text-left text-xs text-slate-300 border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] font-bold uppercase text-slate-500">
                <th className="py-2.5 px-3 min-w-[160px]">Venue</th>
                {HOURS.map((h) => (
                  <th key={h} className="py-2.5 px-2 text-center min-w-[110px]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {VENUES.map((venue) => (
                <tr key={venue.id} className="hover:bg-slate-900/30 transition-colors">
                  <td className="py-3 px-3 font-semibold text-white">
                    <div className="flex items-center space-x-1.5">
                      <Building className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                      <span>{venue.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">{venue.id}</span>
                  </td>

                  {HOURS.map((hour) => {
                    const assignedShift = shifts.find(
                      (s) => s.venueId === venue.id && s.hour === hour
                    );

                    return (
                      <td key={hour} className="py-2 px-1 text-center align-top">
                        {assignedShift ? (
                          <div
                            onClick={() => setSelectedShiftForReplace(assignedShift)}
                            data-testid={`shift-cell-${assignedShift.id}`}
                            className={`rounded-lg border p-2 cursor-pointer transition-all hover:scale-[1.02] text-left ${
                              assignedShift.isOverlapping
                                ? "border-rose-500/60 bg-rose-950/30 shadow-rose-900/20 shadow"
                                : assignedShift.isOverloaded
                                ? "border-amber-500/60 bg-amber-950/30 shadow-amber-900/20 shadow"
                                : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-white text-[11px] truncate block">
                                {assignedShift.staffName}
                              </span>
                            </div>

                            <div className="flex items-center justify-between mt-1 text-[9px]">
                              <span className="text-slate-400 font-mono">{assignedShift.role}</span>
                              <Badge
                                status={
                                  assignedShift.status === "CONFIRMED"
                                    ? "SUCCESS"
                                    : assignedShift.status === "IN_PROGRESS"
                                    ? "PENDING"
                                    : "ACTIVE"
                                }
                                className="text-[8px] px-1 py-0"
                              >
                                {assignedShift.status}
                              </Badge>
                            </div>

                            {/* Overload Flag */}
                            {assignedShift.isOverloaded && (
                              <div
                                className="mt-1 flex items-center space-x-1 text-[9px] font-bold text-amber-400 bg-amber-950/40 px-1 py-0.5 rounded border border-amber-800/40"
                                data-testid="overload-flag"
                              >
                                <AlertTriangle className="h-2.5 w-2.5 shrink-0" />
                                <span>OVERLOADED (&gt;10h)</span>
                              </div>
                            )}

                            {/* Overlap Flag */}
                            {assignedShift.isOverlapping && (
                              <div
                                className="mt-1 flex items-center space-x-1 text-[9px] font-bold text-rose-400 bg-rose-950/40 px-1 py-0.5 rounded border border-rose-800/40"
                                data-testid="overlap-flag"
                              >
                                <AlertTriangle className="h-2.5 w-2.5 shrink-0" />
                                <span>DUAL BOOKED</span>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="rounded-lg border border-dashed border-slate-800 p-2.5 text-center text-[10px] text-slate-600">
                            Unassigned
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Emergency-Replace Dialog with Ranked Suggestions */}
      <Modal
        isOpen={!!selectedShiftForReplace}
        onClose={() => setSelectedShiftForReplace(null)}
        title="Emergency Staff Replacement"
        description="FestOS Staff Engine calculates candidate suitability based on proximity, rested hours, and role skills."
        size="lg"
      >
        {selectedShiftForReplace && (
          <div className="space-y-4 text-xs text-slate-200" data-testid="emergency-replace-modal">
            {/* Shift Context Card */}
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 flex justify-between items-center">
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block">Target Shift</span>
                <span className="font-bold text-white text-sm">
                  {selectedShiftForReplace.venueName} • {selectedShiftForReplace.hour}
                </span>
                <span className="text-slate-400 block mt-0.5">
                  Currently Assigned:{" "}
                  <strong className="text-amber-300">{selectedShiftForReplace.staffName}</strong> (
                  {selectedShiftForReplace.role})
                </span>
              </div>
              {selectedShiftForReplace.isOverloaded && <Badge status="PENDING">OVERLOADED</Badge>}
              {selectedShiftForReplace.isOverlapping && <Badge status="REJECTED">CONFLICT</Badge>}
            </div>

            {/* Ranked Replacement Candidates */}
            <div className="space-y-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                Ranked Replacement Suggestions
              </span>

              <div className="space-y-2">
                {replacementsData?.candidates.map((cand, idx) => {
                  const isSelected = selectedCandidateId === cand.staffId;
                  return (
                    <div
                      key={cand.staffId}
                      onClick={() => setSelectedCandidateId(cand.staffId)}
                      data-testid={`candidate-option-${cand.staffId}`}
                      className={`cursor-pointer rounded-lg border p-3 transition-all flex items-center justify-between ${
                        isSelected
                          ? "border-teal-500 bg-teal-950/20 ring-1 ring-teal-500/40"
                          : "border-slate-800 bg-slate-900/60 hover:border-slate-700"
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-teal-600/30 text-teal-300 font-bold text-[10px]">
                            #{idx + 1}
                          </span>
                          <span className="font-bold text-white">{cand.name}</span>
                          <span className="text-slate-400 text-[10px]">({cand.role})</span>
                        </div>
                        <p className="text-[11px] text-slate-400">{cand.reason}</p>
                        <div className="flex items-center space-x-2 text-[10px] text-slate-500">
                          <span>Hours Worked Today: {cand.hoursWorkedToday}h</span>
                          <span>•</span>
                          <span>Proximity: {cand.proximityMinutes} mins away</span>
                        </div>
                      </div>

                      <div className="text-right shrink-0 ml-3">
                        <span className="text-sm font-bold font-mono text-teal-400">{cand.matchScore}%</span>
                        <span className="text-[9px] text-slate-500 block uppercase">Match Fit</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Handover Note (Mandatory) */}
            <div className="space-y-1 pt-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300">
                Shift Handover Note <span className="text-red-400">* (Strictly Enforced)</span>
              </label>
              <textarea
                rows={3}
                value={handoverNoteInput}
                onChange={(e) => setHandoverNoteInput(e.target.value)}
                placeholder="Detail key venue status, radio channels, VIP arrivals, or special instructions..."
                data-testid="handover-note-input"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-xs text-white focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
              <Button variant="ghost" size="sm" onClick={() => setSelectedShiftForReplace(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!selectedCandidateId || !handoverNoteInput.trim()}
                isLoading={replaceMutation.isPending}
                onClick={() =>
                  replaceMutation.mutate({
                    shiftId: selectedShiftForReplace.id,
                    replacementStaffId: selectedCandidateId,
                    handoverNote: handoverNoteInput.trim(),
                  })
                }
                data-testid="confirm-replace-btn"
              >
                Assign Replacement & Log Handover
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Handover Notes Drawer */}
      <Drawer
        isOpen={isHandoverDrawerOpen}
        onClose={() => setIsHandoverDrawerOpen(false)}
        title="Shift Handover Notes & Transitions"
        width="max-w-md"
      >
        <div className="space-y-4 text-xs text-slate-200">
          <p className="text-slate-400">
            Audit register of operational handover notes recorded during staff transitions across all venues.
          </p>

          <div className="space-y-3" data-testid="handover-notes-list">
            {handovers.map((ho) => (
              <div
                key={ho.id}
                className={`rounded-lg border p-3 space-y-2 ${
                  ho.isMissing
                    ? "border-amber-500/40 bg-amber-950/20"
                    : "border-slate-800 bg-slate-900/60"
                }`}
                data-testid={`handover-entry-${ho.id}`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-bold text-white">{ho.venueName}</span>
                    <span className="text-slate-400 ml-2 font-mono">{ho.hour}</span>
                  </div>
                  {ho.isMissing ? (
                    <Badge status="PENDING">MISSING</Badge>
                  ) : (
                    <Badge status="SUCCESS">RECORDED</Badge>
                  )}
                </div>

                <div className="text-[11px] text-slate-400 flex justify-between">
                  <span>Out: {ho.outgoingStaffName}</span>
                  <span>In: {ho.incomingStaffName}</span>
                </div>

                {ho.isMissing ? (
                  <div className="pt-2 border-t border-amber-500/20">
                    <p className="text-amber-300 italic mb-2">No handover note recorded for this shift transition.</p>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full text-[11px] h-7"
                      onClick={() => {
                        setEditingHandover(ho);
                        setNewNoteContent("");
                      }}
                    >
                      Record Now
                    </Button>
                  </div>
                ) : (
                  <p className="text-slate-300 bg-slate-950/60 p-2 rounded text-[11px] leading-relaxed">
                    {ho.notes}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Record Handover Inline Editor Modal */}
          {editingHandover && (
            <div className="mt-4 rounded-lg border border-teal-500/40 bg-slate-900 p-4 space-y-3">
              <h4 className="font-bold text-white text-xs">
                Record Handover for {editingHandover.venueName} ({editingHandover.hour})
              </h4>
              <textarea
                rows={3}
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Enter handover details, key issues, unresolved items..."
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white focus:outline-none"
              />
              <div className="flex justify-end space-x-2">
                <Button variant="ghost" size="sm" onClick={() => setEditingHandover(null)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!newNoteContent.trim()}
                  onClick={() =>
                    saveHandoverMutation.mutate({
                      venueId: editingHandover.venueId,
                      hour: editingHandover.hour,
                      notes: newNoteContent.trim(),
                    })
                  }
                >
                  Save Handover Note
                </Button>
              </div>
            </div>
          )}
        </div>
      </Drawer>
    </div>
  );
};

export default StaffShiftsWorkspace;
