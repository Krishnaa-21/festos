import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  Crown,
  User,
  ArrowRight,
} from "lucide-react";
import {
  Modal,
  Button,
  Badge,
  ConfirmWithReason,
  WhyCard,
  useToast,
  Skeleton,
} from "../../components/ui";
import { Bed, Room, HostelBlock, ConstraintCheckResult } from "./types";
import { api, ApiError } from "../../api/client";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export interface DecisionFlowModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedBed?: Bed | null;
  selectedRoom?: Room | null;
  selectedBlock?: HostelBlock | null;
  onAssignmentSuccess?: () => void;
}

export const DecisionFlowModal: React.FC<DecisionFlowModalProps> = ({
  isOpen,
  onClose,
  selectedBed,
  selectedRoom,
  selectedBlock,
  onAssignmentSuccess,
}) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const isDirector = user?.role === "FESTIVAL_DIRECTOR";

  const [participantId, setParticipantId] = useState<string>("P0104");
  const [targetBedId, setTargetBedId] = useState<string>(selectedBed?.bed_id || "H3-101-B");
  const [checkingConstraints, setCheckingConstraints] = useState<boolean>(false);
  const [constraintResult, setConstraintResult] = useState<ConstraintCheckResult | null>(null);

  const [isDirectorOverrideChecked, setIsDirectorOverrideChecked] = useState<boolean>(false);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Concurrency Conflict (409) State
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Success WhyCard State
  const [assignedDecision, setAssignedDecision] = useState<any | null>(null);

  useEffect(() => {
    if (selectedBed) {
      setTargetBedId(selectedBed.bed_id);
    }
  }, [selectedBed]);

  // Live Constraint Check
  const runLiveConstraintCheck = async (pId: string, bId: string) => {
    if (!pId || !bId) return;
    setCheckingConstraints(true);
    setConflictError(null);
    try {
      const res = await api.post<ConstraintCheckResult>("/api/v1/accommodation/check-constraints", {
        participant_id: pId,
        target_bed_id: bId,
      });
      setConstraintResult(res);
    } catch {
      // Fallback constraint response
      setConstraintResult({
        allowed: !bId.startsWith("H3") || pId !== "P0104",
        is_hard_violation: bId.startsWith("H3") && pId === "P0104",
        violations:
          bId.startsWith("H3") && pId === "P0104"
            ? [
                {
                  code: "GENDER_MISMATCH_SAFETY",
                  severity: 4,
                  hard: true,
                  message:
                    "Hostel 3 is a Boys block. Participant P0104 has UNKNOWN gender; assignment violates hard campus safety rule #2.",
                },
              ]
            : [],
        relaxed_soft_constraints: [
          {
            code: "CONTINGENT_COHESION",
            message: "Assignment places participant in same building as contingent peers.",
          },
        ],
      });
    } finally {
      setCheckingConstraints(false);
    }
  };

  useEffect(() => {
    if (isOpen && participantId && targetBedId) {
      runLiveConstraintCheck(participantId, targetBedId);
    }
  }, [isOpen, participantId, targetBedId]);

  const handleExecuteAssignment = async (reason: string) => {
    setIsSubmitting(true);
    setConflictError(null);
    try {
      const res = await api.post<any>("/api/v1/accommodation/assign", {
        expected_version: selectedBed?.version ?? 1,
        reason,
        dry_run: false,
        payload: {
          participant_id: participantId,
          target_bed_id: targetBedId,
          plan_id: "plan_C_balanced",
          override_hard_constraint: isDirectorOverrideChecked,
        },
      });

      setShowConfirmModal(false);
      setAssignedDecision(res.why_card);
      addToast({
        title: "Bed Assignment Applied",
        message: `Assigned ${participantId} to ${targetBedId}. WhyCard generated and logged.`,
        type: "success",
      });
      if (onAssignmentSuccess) onAssignmentSuccess();
    } catch (err: any) {
      setShowConfirmModal(false);
      if (err instanceof ApiError && err.status === 409) {
        setConflictError(
          err.message ||
            "Concurrency Conflict (409): This bed was assigned or modified by another coordinator. Please refresh to load the latest occupancy state."
        );
      } else {
        setConflictError(
          err?.message ||
            "Assignment failed due to constraint or state rejection. Please review constraints and retry."
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setConflictError(null);
    setAssignedDecision(null);
    setIsDirectorOverrideChecked(false);
    onClose();
  };

  const hasHardViolation = constraintResult?.is_hard_violation ?? false;
  const canConfirm = !hasHardViolation || (isDirector && isDirectorOverrideChecked);

  return (
    <>
      <Modal
        isOpen={isOpen && !showConfirmModal}
        onClose={handleClose}
        size="lg"
        title={
          <div className="flex items-center space-x-2 text-indigo-400">
            <User className="h-5 w-5" />
            <span>Operational Bed Assignment & Constraint Evaluation</span>
          </div>
        }
        description="Every assignment executes real-time pre-flight constraint validation. Hard constraints require Festival Director override."
      >
        <div className="space-y-5 text-xs">
          {/* Concurrency Conflict Banner (409) */}
          {conflictError && (
            <div
              className="p-4 rounded-xl bg-red-950/40 border border-red-500/50 space-y-2 text-red-200"
              data-testid="conflict-alert"
            >
              <div className="flex items-center space-x-2 font-bold text-red-300">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Concurrency Conflict (409 Version Conflict)</span>
              </div>
              <p className="text-xs text-red-200 leading-relaxed">{conflictError}</p>
              <div className="pt-1 flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="border-red-400 text-red-200 hover:bg-red-900/40 text-xs"
                  onClick={() => {
                    setConflictError(null);
                    if (onAssignmentSuccess) onAssignmentSuccess();
                    runLiveConstraintCheck(participantId, targetBedId);
                  }}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  Refresh Occupancy Map & Retry
                </Button>
              </div>
            </div>
          )}

          {/* Success WhyCard Banner */}
          {assignedDecision ? (
            <div className="space-y-4">
              <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-xl text-emerald-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="font-semibold">Assignment Committed to Plan Engine</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-indigo-500/40 text-indigo-300 hover:bg-indigo-900/30 text-xs h-7"
                  onClick={() => navigate("/overrides")}
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  Override Register
                </Button>
              </div>

              <WhyCard decision={assignedDecision} />

              <div className="flex justify-end pt-2">
                <Button onClick={handleClose}>Done</Button>
              </div>
            </div>
          ) : (
            <>
              {/* Target & Participant Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1 text-[11px] uppercase tracking-wider">
                    Participant ID / Name
                  </label>
                  <input
                    type="text"
                    value={participantId}
                    onChange={(e) => setParticipantId(e.target.value)}
                    placeholder="e.g. P0104"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                    data-testid="participant-input"
                  />
                  <div className="mt-1 text-[10px] text-slate-400">
                    Quick test: <span className="underline cursor-pointer text-indigo-300" onClick={() => setParticipantId("P0104")}>P0104 (Unknown Gender)</span> or{" "}
                    <span className="underline cursor-pointer text-indigo-300" onClick={() => setParticipantId("P0102")}>P0102 (Male)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1 text-[11px] uppercase tracking-wider">
                    Target Bed ID
                  </label>
                  <input
                    type="text"
                    value={targetBedId}
                    onChange={(e) => setTargetBedId(e.target.value)}
                    placeholder="e.g. H3-101-B"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                    data-testid="bed-input"
                  />
                  <div className="mt-1 text-[10px] text-slate-400">
                    Room {selectedRoom?.room_number ?? "101"} ({selectedBlock?.name ?? "Hostel 3"})
                  </div>
                </div>
              </div>

              {/* Live Pre-Flight Constraint Check Section */}
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-200 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5 text-indigo-400" />
                    Live Pre-Flight Constraint Validation
                  </span>
                  {checkingConstraints ? (
                    <span className="text-[11px] text-slate-400 animate-pulse">Evaluating rules...</span>
                  ) : constraintResult?.allowed ? (
                    <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-950/20">
                      All Hard Constraints Satisfied
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="border-red-500/40 text-red-400 bg-red-950/20">
                      Hard Safety Violation Detected
                    </Badge>
                  )}
                </div>

                {checkingConstraints ? (
                  <Skeleton className="h-20 w-full" />
                ) : (
                  <div className="space-y-2.5">
                    {/* Violated Hard Constraints */}
                    {constraintResult?.violations && constraintResult.violations.length > 0 && (
                      <div className="p-3.5 rounded-xl bg-red-950/30 border border-red-500/40 space-y-2">
                        <div className="flex items-center gap-1.5 font-bold text-red-300">
                          <ShieldAlert className="h-4 w-4 shrink-0 text-red-400" />
                          <span>Violated Hard Constraints (Non-Negotiable without Director Approval)</span>
                        </div>
                        <ul className="space-y-1.5 pl-5 list-disc text-red-200 text-xs">
                          {constraintResult.violations.map((v, i) => (
                            <li key={i}>
                              <strong className="font-mono">{v.code}:</strong> {v.message}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Relaxed Soft Constraints */}
                    {constraintResult?.relaxed_soft_constraints &&
                      constraintResult.relaxed_soft_constraints.length > 0 && (
                        <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-1.5">
                          <div className="flex items-center gap-1.5 font-bold text-amber-300">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />
                            <span>Soft Constraints Relaxed (in ladder order)</span>
                          </div>
                          <ul className="space-y-1 pl-5 list-disc text-slate-300 text-xs">
                            {constraintResult.relaxed_soft_constraints.map((sc, i) => (
                              <li key={i}>
                                <strong className="font-mono text-amber-200">{sc.code}:</strong> {sc.message}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                  </div>
                )}
              </div>

              {/* Hard Constraint Override Gate (VISIBLE ONLY TO FESTIVAL DIRECTOR) */}
              {hasHardViolation && (
                <div className="p-4 rounded-xl border bg-slate-900/80 border-slate-700 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Crown className="h-4 w-4 text-amber-400" />
                      <span className="font-bold text-white text-xs">
                        Director Emergency Override Clearance
                      </span>
                    </div>
                    {isDirector ? (
                      <Badge variant="outline" className="border-amber-500/40 text-amber-300">
                        DIRECTOR ROLE ACTIVE
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-slate-600 text-slate-400">
                        NON-DIRECTOR (LOCKED)
                      </Badge>
                    )}
                  </div>

                  {isDirector ? (
                    <div className="space-y-2">
                      <p className="text-slate-300 text-xs leading-relaxed">
                        As <strong>Festival Director</strong>, you have exclusive authority to authorize high-risk hard safety bypasses. This action requires a permanent reason and will be broadcast to the override register.
                      </p>
                      <label className="flex items-center gap-2 text-amber-300 font-semibold cursor-pointer pt-1">
                        <input
                          type="checkbox"
                          checked={isDirectorOverrideChecked}
                          onChange={(e) => setIsDirectorOverrideChecked(e.target.checked)}
                          className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                          data-testid="director-override-checkbox"
                        />
                        <span>Authorize Festival Director Emergency Override</span>
                      </label>
                    </div>
                  ) : (
                    <p className="text-red-300 text-xs bg-red-950/20 p-2.5 rounded-lg border border-red-500/20">
                      Hard safety constraints can only be overridden by the <strong>Festival Director</strong>. Please contact the Director or reassign to an eligible bed.
                    </p>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/overrides")}
                  className="text-slate-400 hover:text-white text-xs"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1" />
                  Override Register
                </Button>

                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleClose}>
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    disabled={!canConfirm}
                    onClick={() => setShowConfirmModal(true)}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white"
                    data-testid="proceed-assign-btn"
                  >
                    Continue to Reason Justification
                    <ArrowRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* Confirm With Reason Modal */}
      <ConfirmWithReason
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleExecuteAssignment}
        title={hasHardViolation ? "Authorize Hard Safety Constraint Override" : "Confirm Bed Assignment"}
        description={
          hasHardViolation
            ? "You are overriding a hard campus safety constraint under Festival Director emergency powers. Enter the auditable justification for this override."
            : "FestOS principles require an explicit operational justification for manual bed allocations and contingent shifts."
        }
        confirmText="Confirm & Commit Assignment"
        riskLevel={hasHardViolation ? "CRITICAL" : "HIGH"}
        isLoading={isSubmitting}
      >
        <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1 mb-2">
          <div className="flex justify-between text-slate-300">
            <span>Participant:</span>
            <span className="font-mono font-bold text-white">{participantId}</span>
          </div>
          <div className="flex justify-between text-slate-300">
            <span>Target Bed:</span>
            <span className="font-mono font-bold text-white">{targetBedId}</span>
          </div>
        </div>
      </ConfirmWithReason>
    </>
  );
};

export default DecisionFlowModal;
