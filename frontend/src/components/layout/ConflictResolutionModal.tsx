import React, { useState } from "react";
import { AlertTriangle, CheckCircle, Trash2, ArrowRight } from "lucide-react";
import { Modal, Button, Badge } from "../ui";
import { QueuedOperation } from "../../pwa/offlineDb";

interface ConflictResolutionModalProps {
  conflict: QueuedOperation | null;
  isOpen: boolean;
  onClose: () => void;
  onResolve: (
    clientOpId: string,
    resolution: "ACCEPT_SERVER" | "FORCE_OVERRIDE" | "DISCARD",
    reason?: string
  ) => void;
}

export const ConflictResolutionModal: React.FC<ConflictResolutionModalProps> = ({
  conflict,
  isOpen,
  onClose,
  onResolve,
}) => {
  const [overrideReason, setOverrideReason] = useState("");
  const [activeAction, setActiveAction] = useState<"ACCEPT" | "OVERRIDE" | null>(null);

  if (!conflict) return null;

  const payload = conflict.payload as any;
  const serverResult = conflict.server_result;

  const handleConfirmOverride = () => {
    if (!overrideReason.trim()) return;
    onResolve(conflict.client_op_id, "FORCE_OVERRIDE", overrideReason.trim());
    onClose();
  };

  const handleAcceptServer = () => {
    onResolve(conflict.client_op_id, "ACCEPT_SERVER");
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Offline Sync Conflict Resolution"
      size="md"
    >
      <div className="space-y-4" data-testid="conflict-resolution-modal">
        {/* Banner */}
        <div className="p-3.5 rounded-xl border border-amber-500/40 bg-amber-950/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <div className="font-bold text-amber-200">
              State Discrepancy Detected During Reconnect Sync
            </div>
            <div className="text-amber-300/80 leading-relaxed">
              {serverResult?.message ||
                "The server rejected this offline operation due to an active lock, prior checkout, or state conflict."}
            </div>
          </div>
        </div>

        {/* Side-by-side comparison */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Client Offline Action
            </div>
            <div className="font-mono text-white font-bold">{conflict.op_type}</div>
            <div className="text-slate-300">
              Participant: <strong className="text-white">{payload.participant_id}</strong>
            </div>
            {payload.wristband_code && (
              <div className="text-slate-400">
                Wristband: <span className="font-mono text-slate-200">{payload.wristband_code}</span>
              </div>
            )}
            {payload.item_id && (
              <div className="text-slate-400">
                Item: <span className="font-mono text-slate-200">{payload.item_id}</span>
              </div>
            )}
            <div className="text-[10px] text-slate-500">
              Queued: {new Date(conflict.created_at).toLocaleTimeString()}
            </div>
          </div>

          <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Server Authoritative State
            </div>
            <div className="flex items-center gap-1.5">
              <Badge variant="solid" status="REJECTED">
                CONFLICT
              </Badge>
              <span className="text-[11px] text-rose-400 font-bold">Unmerged</span>
            </div>
            <div className="text-slate-400 text-[11px]">
              {serverResult?.conflict_details?.server_status ||
                "Record modified concurrently by desk supervisor."}
            </div>
            <div className="text-[10px] text-slate-500">
              Policy: Server state wins until human sign-off
            </div>
          </div>
        </div>

        {/* Action Choice Tabs */}
        <div className="pt-2 border-t border-slate-800 space-y-3">
          <div className="text-xs font-semibold text-slate-300">
            Select Resolution Policy:
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              data-testid="resolve-accept-server-btn"
              onClick={() => setActiveAction("ACCEPT")}
              className={`p-3 rounded-lg border text-left text-xs transition-all ${
                activeAction === "ACCEPT"
                  ? "border-emerald-500 bg-emerald-950/30 text-white"
                  : "border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white"
              }`}
            >
              <div className="font-bold text-emerald-400 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4" />
                Accept Server State
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Discards local operation. Preserves current server record without modification.
              </div>
            </button>

            <button
              type="button"
              data-testid="resolve-force-override-btn"
              onClick={() => setActiveAction("OVERRIDE")}
              className={`p-3 rounded-lg border text-left text-xs transition-all ${
                activeAction === "OVERRIDE"
                  ? "border-amber-500 bg-amber-950/30 text-white"
                  : "border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white"
              }`}
            >
              <div className="font-bold text-amber-400 flex items-center gap-1.5">
                <ArrowRight className="w-4 h-4" />
                Force Override
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Re-submits with human justification recorded in the override audit log.
              </div>
            </button>
          </div>

          {activeAction === "OVERRIDE" && (
            <div className="space-y-2 pt-2 animate-fadeIn">
              <label className="block text-xs font-medium text-slate-300">
                Mandatory Override Justification <span className="text-rose-400">*</span>
              </label>
              <textarea
                data-testid="conflict-override-reason"
                rows={2}
                placeholder="Explain why this offline operation takes precedence..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                className="w-full text-xs rounded-lg border border-slate-700 bg-slate-900 p-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              onResolve(conflict.client_op_id, "DISCARD");
              onClose();
            }}
            className="text-rose-400 hover:text-rose-300 hover:border-rose-800"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            Discard Op
          </Button>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            {activeAction === "ACCEPT" && (
              <Button
                data-testid="confirm-accept-server-btn"
                variant="primary"
                size="sm"
                onClick={handleAcceptServer}
              >
                Confirm Accept Server
              </Button>
            )}
            {activeAction === "OVERRIDE" && (
              <Button
                data-testid="confirm-force-override-btn"
                variant="primary"
                size="sm"
                disabled={!overrideReason.trim()}
                onClick={handleConfirmOverride}
              >
                Apply Override
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
};
