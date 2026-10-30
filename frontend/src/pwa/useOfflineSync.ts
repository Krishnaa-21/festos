import { useState, useEffect, useCallback } from "react";
import { offlineDb, QueuedOperation } from "./offlineDb";
import { synchronizeOfflineQueue, SyncBatchResult } from "./syncService";

export interface UseOfflineSyncReturn {
  isOnline: boolean;
  pendingCount: number;
  pendingOps: QueuedOperation[];
  allOps: QueuedOperation[];
  lastSyncedAt: string | null;
  isSyncing: boolean;
  conflicts: QueuedOperation[];
  syncNow: () => Promise<SyncBatchResult>;
  resolveConflict: (
    clientOpId: string,
    resolution: "ACCEPT_SERVER" | "FORCE_OVERRIDE" | "DISCARD",
    reason?: string
  ) => Promise<void>;
  clearCompleted: () => Promise<void>;
}

export function useOfflineSync(): UseOfflineSyncReturn {
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [pendingOps, setPendingOps] = useState<QueuedOperation[]>([]);
  const [allOps, setAllOps] = useState<QueuedOperation[]>([]);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [conflicts, setConflicts] = useState<QueuedOperation[]>([]);

  const refreshState = useCallback(async () => {
    try {
      const count = await offlineDb.getPendingCount();
      const pending = await offlineDb.getPendingOps();
      const all = await offlineDb.getAllOps();
      const lastSync = await offlineDb.getLastSyncedAt();

      setPendingCount(count);
      setPendingOps(pending);
      setAllOps(all);
      setLastSyncedAt(lastSync);

      const conflictList = all.filter((op) => op.status === "CONFLICT");
      setConflicts(conflictList);
    } catch {
      // IndexedDB may not be ready in certain environments
    }
  }, []);

  const syncNow = useCallback(async (): Promise<SyncBatchResult> => {
    setIsSyncing(true);
    try {
      const result = await synchronizeOfflineQueue();
      await refreshState();
      return result;
    } finally {
      setIsSyncing(false);
    }
  }, [refreshState]);

  const resolveConflict = useCallback(
    async (
      clientOpId: string,
      resolution: "ACCEPT_SERVER" | "FORCE_OVERRIDE" | "DISCARD",
      reason?: string
    ) => {
      await offlineDb.resolveConflict(clientOpId, resolution, reason);
      await refreshState();
    },
    [refreshState]
  );

  const clearCompleted = useCallback(async () => {
    await offlineDb.clearCompletedOps();
    await refreshState();
  }, [refreshState]);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      // Automatic sync on reconnect as required by Section 6.11
      syncNow();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    const handleSyncCompleted = () => {
      refreshState();
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("festos:sync_completed", handleSyncCompleted);

    refreshState();

    // Poll IndexedDB periodically (every 5 seconds) to keep count fresh
    const interval = setInterval(refreshState, 5000);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("festos:sync_completed", handleSyncCompleted);
      clearInterval(interval);
    };
  }, [refreshState, syncNow]);

  return {
    isOnline,
    pendingCount,
    pendingOps,
    allOps,
    lastSyncedAt,
    isSyncing,
    conflicts,
    syncNow,
    resolveConflict,
    clearCompleted,
  };
}
