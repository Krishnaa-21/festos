import React, { useState } from "react";
import {
  Wifi,
  WifiOff,
  RefreshCw,
  AlertOctagon,
  Trash2,
} from "lucide-react";
import { useOfflineSync } from "../../pwa/useOfflineSync";
import { QueuedOperation } from "../../pwa/offlineDb";
import { Modal, Button, Badge } from "../ui";
import { ConflictResolutionModal } from "./ConflictResolutionModal";

export const OfflineStatusPill: React.FC = () => {
  const {
    isOnline,
    pendingCount,
    allOps,
    lastSyncedAt,
    isSyncing,
    syncNow,
    resolveConflict,
    clearCompleted,
  } = useOfflineSync();

  const [isQueueModalOpen, setIsQueueModalOpen] = useState(false);
  const [selectedConflict, setSelectedConflict] = useState<QueuedOperation | null>(null);

  const formattedLastSync = lastSyncedAt
    ? new Date(lastSyncedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "Never";

  return (
    <>
      <div className="flex items-center gap-2">
        {/* Status indicator pill */}
        <button
          type="button"
          data-testid="offline-status-indicator"
          onClick={() => setIsQueueModalOpen(true)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
            isOnline
              ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/40"
              : "bg-rose-950/40 text-rose-300 border-rose-500/40 hover:bg-rose-900/40 animate-pulse"
          }`}
          title="Click to view offline queue & sync status"
        >
          {isOnline ? (
            <>
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
              <span data-testid="offline-status-online" className="hidden sm:inline">
                Online
              </span>
              <span className="text-[10px] text-slate-400 font-mono hidden md:inline">
                · {formattedLastSync}
              </span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-rose-400" />
              <span data-testid="offline-status-offline">Offline</span>
            </>
          )}

          {/* Pending badge */}
          {pendingCount > 0 && (
            <span
              data-testid="offline-pending-badge"
              className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-amber-500 text-slate-950 shadow-sm"
            >
              {pendingCount} queued
            </span>
          )}
        </button>
      </div>

      {/* Offline Queue Modal */}
      {isQueueModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setIsQueueModalOpen(false)}
          title="Offline Queue & Sync Management (Dexie IndexedDB)"
          size="lg"
        >
          <div className="space-y-4" data-testid="offline-queue-modal">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border border-slate-800 bg-slate-900/60">
              <div className="text-xs space-y-0.5">
                <div className="text-slate-300">
                  Network State:{" "}
                  <strong className={isOnline ? "text-emerald-400" : "text-rose-400"}>
                    {isOnline ? "Connected (Wi-Fi / Mobile Data)" : "Disconnected (Offline Mode Active)"}
                  </strong>
                </div>
                <div className="text-slate-400 font-mono text-[11px]">
                  Last synced: {formattedLastSync} · Device ID: {allOps[0]?.device_id || "epinoia_vol_01"}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  data-testid="manual-sync-btn"
                  variant="primary"
                  size="sm"
                  disabled={isSyncing || !isOnline}
                  onClick={async () => {
                    await syncNow();
                  }}
                  className="text-xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 mr-1 ${isSyncing ? "animate-spin" : ""}`} />
                  {isSyncing ? "Syncing..." : "Sync Now"}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearCompleted}
                  className="text-xs"
                  title="Clear applied operations from queue"
                >
                  <Trash2 className="w-3.5 h-3.5 mr-1" />
                  Clear Synced
                </Button>
              </div>
            </div>

            {/* List of operations */}
            <div className="space-y-2">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>Queued Operations ({allOps.length})</span>
                <span className="text-[11px] text-slate-500 lowercase">safe ops only (check-in, merch)</span>
              </div>

              {allOps.length === 0 ? (
                <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
                  Offline queue is empty. Operations performed while offline will be buffered here safely.
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {allOps.map((op) => {
                    const payload = op.payload as any;
                    return (
                      <div
                        key={op.client_op_id}
                        data-testid={`queued-op-${op.client_op_id}`}
                        className={`p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                          op.status === "APPLIED"
                            ? "border-emerald-500/30 bg-emerald-950/20"
                            : op.status === "DUPLICATE_IGNORED"
                            ? "border-amber-500/30 bg-amber-950/20"
                            : op.status === "CONFLICT"
                            ? "border-rose-500/40 bg-rose-950/30"
                            : "border-slate-800 bg-slate-900/60"
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-white text-[11px]">
                              {op.op_type}
                            </span>
                            <Badge
                              variant="solid"
                              status={
                                op.status === "APPLIED"
                                  ? "SUCCESS"
                                  : op.status === "DUPLICATE_IGNORED"
                                  ? "PENDING"
                                  : op.status === "CONFLICT"
                                  ? "REJECTED"
                                  : "PENDING"
                              }
                            >
                              {op.status}
                            </Badge>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {new Date(op.created_at).toLocaleTimeString()}
                            </span>
                          </div>

                          <div className="text-slate-300">
                            Participant ID:{" "}
                            <strong className="text-white font-mono">{payload.participant_id}</strong>
                            {payload.item_id && (
                              <span className="ml-2 text-slate-400">
                                Item: <span className="font-mono text-slate-200">{payload.item_id}</span>
                              </span>
                            )}
                            {payload.wristband_code && (
                              <span className="ml-2 text-slate-400">
                                Band: <span className="font-mono text-slate-200">{payload.wristband_code}</span>
                              </span>
                            )}
                          </div>

                          {op.server_result?.message && (
                            <div className="text-[11px] text-slate-400 italic">
                              Server explanation: {op.server_result.message}
                            </div>
                          )}
                        </div>

                        {op.status === "CONFLICT" && (
                          <Button
                            data-testid={`resolve-conflict-${op.client_op_id}`}
                            variant="primary"
                            size="sm"
                            onClick={() => setSelectedConflict(op)}
                            className="bg-rose-600 hover:bg-rose-700 text-xs shrink-0"
                          >
                            <AlertOctagon className="w-3.5 h-3.5 mr-1" />
                            Resolve Conflict
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-500 p-2.5 rounded bg-slate-950/60 border border-slate-800 leading-relaxed">
              <strong>FestOS Section 6.11 Policy:</strong> Safe operations are stored with client op UUIDs and synchronized automatically upon reconnect. Conflicting records require human sign-off; duplicate requests are idempotently acknowledged.
            </div>
          </div>
        </Modal>
      )}

      {/* Conflict Resolution Modal */}
      {selectedConflict && (
        <ConflictResolutionModal
          isOpen={true}
          conflict={selectedConflict}
          onClose={() => setSelectedConflict(null)}
          onResolve={async (opId, resolution, reason) => {
            await resolveConflict(opId, resolution, reason);
            setSelectedConflict(null);
          }}
        />
      )}
    </>
  );
};
