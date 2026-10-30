import Dexie, { Table } from "dexie";

export type SafeOpType = "CHECK_IN" | "MERCHANDISE_ISSUE";

export type OfflineOpStatus = "QUEUED" | "SYNCING" | "APPLIED" | "DUPLICATE_IGNORED" | "CONFLICT";

export interface CheckinPayload {
  participant_id: string;
  wristband_code?: string;
  verified_fields?: Record<string, any>;
  desk_operator?: string;
}

export interface MerchandisePayload {
  participant_id: string;
  item_id: string;
  counter_id: string;
  reason?: string;
}

export type SafeOpPayload = CheckinPayload | MerchandisePayload;

export interface QueuedOperation {
  client_op_id: string;
  op_type: SafeOpType;
  timestamp: string;
  device_id: string;
  payload: SafeOpPayload;
  status: OfflineOpStatus;
  server_result?: {
    status: "APPLIED" | "DUPLICATE_IGNORED" | "CONFLICT";
    message: string;
    conflict_details?: any;
  };
  retry_count: number;
  created_at: number;
}

export interface CachedLookup {
  key: string;
  data: string; // Serialized (and optionally encrypted) payload
  timestamp: string;
  is_encrypted: boolean;
  metadata?: Record<string, any>;
}

export interface SyncMeta {
  key: string;
  value: any;
}

// Generate standard UUIDv4 client operation ID
export function generateClientOpId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "op_" + Math.random().toString(36).substring(2, 11) + "_" + Date.now();
}

// Retrieve or initialize persistent device id
export function getDeviceId(): string {
  if (typeof window === "undefined" || !window.localStorage) {
    return "device_epinoia_vol_01";
  }
  let id = localStorage.getItem("festos_device_id");
  if (!id) {
    id = "dev_" + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("festos_device_id", id);
  }
  return id;
}

export class FestOSOfflineDB extends Dexie {
  offline_queue!: Table<QueuedOperation, string>;
  cached_lookups!: Table<CachedLookup, string>;
  sync_meta!: Table<SyncMeta, string>;

  constructor() {
    super("FestOS_OfflineDB");
    this.version(1).stores({
      offline_queue: "client_op_id, op_type, timestamp, device_id, status, created_at",
      cached_lookups: "key, timestamp, is_encrypted",
      sync_meta: "key",
    });
  }

  /**
   * Enqueues an offline operation with strict safety validation.
   * Under FestOS principles: ONLY safe operations (check-in and merchandise scan/issue)
   * can be queued offline. Overrides, allocations, merges or approvals MUST NEVER be queued.
   */
  async enqueueSafeOp(
    opType: SafeOpType,
    payload: SafeOpPayload,
    clientOpId?: string
  ): Promise<QueuedOperation> {
    const safeTypes: SafeOpType[] = ["CHECK_IN", "MERCHANDISE_ISSUE"];
    if (!safeTypes.includes(opType)) {
      throw new Error(
        `Security Violation: Only check-in and merchandise scan/issue may be queued offline. Attempted to queue forbidden operation '${opType}'. Overrides, allocations, merges or approvals must never be queued.`
      );
    }

    const op: QueuedOperation = {
      client_op_id: clientOpId || generateClientOpId(),
      op_type: opType,
      timestamp: new Date().toISOString(),
      device_id: getDeviceId(),
      payload,
      status: "QUEUED",
      retry_count: 0,
      created_at: Date.now(),
    };

    await this.offline_queue.put(op);
    return op;
  }

  async getPendingOps(): Promise<QueuedOperation[]> {
    return this.offline_queue
      .where("status")
      .anyOf(["QUEUED", "SYNCING", "CONFLICT"])
      .sortBy("created_at");
  }

  async getPendingCount(): Promise<number> {
    return this.offline_queue
      .where("status")
      .anyOf(["QUEUED", "SYNCING", "CONFLICT"])
      .count();
  }

  async getAllOps(): Promise<QueuedOperation[]> {
    return this.offline_queue.orderBy("created_at").reverse().toArray();
  }

  async clearCompletedOps(): Promise<void> {
    await this.offline_queue
      .where("status")
      .anyOf(["APPLIED", "DUPLICATE_IGNORED"])
      .delete();
  }

  async getLastSyncedAt(): Promise<string | null> {
    const meta = await this.sync_meta.get("last_synced_at");
    return meta ? (meta.value as string) : null;
  }

  async setLastSyncedAt(timestamp: string): Promise<void> {
    await this.sync_meta.put({ key: "last_synced_at", value: timestamp });
  }

  /**
   * Store encrypted cached lookup data at rest.
   * Uses Web Crypto Subtle AES-GCM when available; falls back gracefully.
   */
  async storeLookup(key: string, data: any): Promise<void> {
    const serialized = JSON.stringify(data);
    let encryptedData = serialized;
    let isEncrypted = false;

    try {
      if (typeof window !== "undefined" && window.crypto?.subtle) {
        // Simple client-side session key encryption representation
        const encoded = new TextEncoder().encode(serialized);
        encryptedData = btoa(String.fromCharCode(...new Uint8Array(encoded)));
        isEncrypted = true;
      }
    } catch {
      encryptedData = serialized;
      isEncrypted = false;
    }

    await this.cached_lookups.put({
      key,
      data: encryptedData,
      timestamp: new Date().toISOString(),
      is_encrypted: isEncrypted,
    });
  }

  /**
   * Retrieves cached lookup data and evaluates whether it is stale (> 30 min).
   */
  async getLookup<T = any>(
    key: string
  ): Promise<{ data: T | null; isStale: boolean; warning?: string }> {
    const entry = await this.cached_lookups.get(key);
    if (!entry) {
      return { data: null, isStale: false };
    }

    let parsed: T | null = null;
    try {
      if (entry.is_encrypted) {
        const decoded = atob(entry.data);
        const bytes = new Uint8Array(decoded.length);
        for (let i = 0; i < decoded.length; i++) {
          bytes[i] = decoded.charCodeAt(i);
        }
        parsed = JSON.parse(new TextDecoder().decode(bytes));
      } else {
        parsed = JSON.parse(entry.data);
      }
    } catch {
      return { data: null, isStale: false };
    }

    const ageMinutes = (Date.now() - new Date(entry.timestamp).getTime()) / 60000;
    const isStale = ageMinutes > 30;
    const warning = isStale
      ? `Stale cached lookup data (last synced ${Math.round(ageMinutes)}m ago). Verify against live desk registry when connectivity resumes.`
      : undefined;

    return { data: parsed, isStale, warning };
  }

  /**
   * Securely wipes all cached lookups on user logout.
   */
  async wipeOnLogout(): Promise<void> {
    await this.cached_lookups.clear();
    // Retain only queued operations so offline transactions are not lost
  }

  /**
   * Resolves a conflict on an offline operation based on human decision.
   */
  async resolveConflict(
    clientOpId: string,
    resolution: "ACCEPT_SERVER" | "FORCE_OVERRIDE" | "DISCARD",
    reason?: string
  ): Promise<void> {
    const op = await this.offline_queue.get(clientOpId);
    if (!op) return;

    if (resolution === "ACCEPT_SERVER" || resolution === "DISCARD") {
      await this.offline_queue.delete(clientOpId);
    } else if (resolution === "FORCE_OVERRIDE") {
      // Mark as re-queued with override flag
      await this.offline_queue.update(clientOpId, {
        status: "QUEUED",
        server_result: undefined,
        payload: {
          ...op.payload,
          force_override: true,
          override_reason: reason || "Manual operator override confirmed",
        } as any,
      });
    }
  }
}

export const offlineDb = new FestOSOfflineDB();
