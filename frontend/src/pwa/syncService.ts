import { offlineDb } from "./offlineDb";
import { api } from "../api/client";

export interface SyncBatchResult {
  totalProcessed: number;
  applied: number;
  duplicatesIgnored: number;
  conflicts: number;
  results: Array<{
    client_op_id: string;
    op_type: "CHECK_IN" | "MERCHANDISE_ISSUE";
    status: "APPLIED" | "DUPLICATE_IGNORED" | "CONFLICT";
    message: string;
    conflict_details?: any;
  }>;
}

export async function synchronizeOfflineQueue(): Promise<SyncBatchResult> {
  const pendingOps = await offlineDb.getPendingOps();
  const summary: SyncBatchResult = {
    totalProcessed: 0,
    applied: 0,
    duplicatesIgnored: 0,
    conflicts: 0,
    results: [],
  };

  if (pendingOps.length === 0) {
    const nowIso = new Date().toISOString();
    await offlineDb.setLastSyncedAt(nowIso);
    return summary;
  }

  // Mark all ops as SYNCING in IndexedDB
  for (const op of pendingOps) {
    await offlineDb.offline_queue.update(op.client_op_id, { status: "SYNCING" });
  }

  // 1. Separate into Check-in and Merchandise batches
  const checkinOps = pendingOps.filter((op) => op.op_type === "CHECK_IN");
  const merchOps = pendingOps.filter((op) => op.op_type === "MERCHANDISE_ISSUE");

  // 2. Sync Check-in Batch
  if (checkinOps.length > 0) {
    try {
      const response = await api.post<any>("/api/v1/checkin/sync", {
        device_id: checkinOps[0].device_id,
        operations: checkinOps.map((op) => ({
          client_op_id: op.client_op_id,
          participant_id: (op.payload as any).participant_id,
          wristband_code: (op.payload as any).wristband_code,
          verified_fields: (op.payload as any).verified_fields || {},
          desk_operator: (op.payload as any).desk_operator || "Volunteer Counter",
          timestamp: op.timestamp,
        })),
      });

      const serverResults: any[] = response?.results || response?.data?.results || [];

      for (const op of checkinOps) {
        summary.totalProcessed++;
        const sRes = serverResults.find((r) => r.client_op_id === op.client_op_id);

        let finalStatus: "APPLIED" | "DUPLICATE_IGNORED" | "CONFLICT" = "APPLIED";
        let message = "Check-in applied cleanly.";
        let conflictDetails = undefined;

        if (sRes) {
          if (sRes.status === "DUPLICATE_IGNORED" || sRes.status === "ALREADY_APPLIED") {
            finalStatus = "DUPLICATE_IGNORED";
            message = sRes.message || "Duplicate check-in ignored (already verified on server).";
            summary.duplicatesIgnored++;
          } else if (sRes.status === "CONFLICT") {
            finalStatus = "CONFLICT";
            message = sRes.message || "Server state conflict detected.";
            conflictDetails = sRes.conflict_details;
            summary.conflicts++;
          } else {
            finalStatus = "APPLIED";
            message = sRes.message || "Check-in applied.";
            summary.applied++;
          }
        } else {
          summary.applied++;
        }

        await offlineDb.offline_queue.update(op.client_op_id, {
          status: finalStatus,
          server_result: {
            status: finalStatus,
            message,
            conflict_details: conflictDetails,
          },
        });

        summary.results.push({
          client_op_id: op.client_op_id,
          op_type: "CHECK_IN",
          status: finalStatus,
          message,
          conflict_details: conflictDetails,
        });
      }
    } catch (err: any) {
      console.warn("Check-in batch sync failed:", err);
      // Revert to QUEUED on network failure
      for (const op of checkinOps) {
        await offlineDb.offline_queue.update(op.client_op_id, {
          status: "QUEUED",
          retry_count: (op.retry_count || 0) + 1,
        });
      }
    }
  }

  // 3. Sync Merchandise Batch
  if (merchOps.length > 0) {
    try {
      const response = await api.post<any>("/api/v1/merchandise/sync", {
        device_id: merchOps[0].device_id,
        operations: merchOps.map((op) => ({
          client_op_id: op.client_op_id,
          participant_id: (op.payload as any).participant_id,
          item_id: (op.payload as any).item_id,
          counter_id: (op.payload as any).counter_id || "OFFLINE_COUNTER",
          reason: (op.payload as any).reason || "Offline counter handover",
          timestamp: op.timestamp,
        })),
      });

      const serverResults: any[] = response?.results || response?.data?.results || [];

      for (const op of merchOps) {
        summary.totalProcessed++;
        const sRes = serverResults.find((r) => r.client_op_id === op.client_op_id);

        let finalStatus: "APPLIED" | "DUPLICATE_IGNORED" | "CONFLICT" = "APPLIED";
        let message = "Merchandise issue applied cleanly.";
        let conflictDetails = undefined;

        if (sRes) {
          if (sRes.status === "DUPLICATE_IGNORED" || sRes.status === "ALREADY_APPLIED") {
            finalStatus = "DUPLICATE_IGNORED";
            message = sRes.message || "Duplicate claim ignored (already issued previously).";
            summary.duplicatesIgnored++;
          } else if (sRes.status === "CONFLICT") {
            finalStatus = "CONFLICT";
            message = sRes.message || "Counter conflict detected.";
            conflictDetails = sRes.conflict_details;
            summary.conflicts++;
          } else {
            finalStatus = "APPLIED";
            message = sRes.message || "Merchandise issue applied.";
            summary.applied++;
          }
        } else {
          summary.applied++;
        }

        await offlineDb.offline_queue.update(op.client_op_id, {
          status: finalStatus,
          server_result: {
            status: finalStatus,
            message,
            conflict_details: conflictDetails,
          },
        });

        summary.results.push({
          client_op_id: op.client_op_id,
          op_type: "MERCHANDISE_ISSUE",
          status: finalStatus,
          message,
          conflict_details: conflictDetails,
        });
      }
    } catch (err: any) {
      console.warn("Merchandise batch sync failed:", err);
      for (const op of merchOps) {
        await offlineDb.offline_queue.update(op.client_op_id, {
          status: "QUEUED",
          retry_count: (op.retry_count || 0) + 1,
        });
      }
    }
  }

  const nowIso = new Date().toISOString();
  await offlineDb.setLastSyncedAt(nowIso);

  // Dispatch custom window event so all UI subscribers can immediately update
  if (typeof window !== "undefined") {
    window.dispatchEvent(
      new CustomEvent("festos:sync_completed", {
        detail: summary,
      })
    );
  }

  return summary;
}
