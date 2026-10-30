export interface StockItem {
  id: string;
  name: string;
  code: string;
  kind: "equipment" | "merch" | "all";
  condition: string;
  location_id: string;
  location_name: string;
  on_hand: number;
  reserved: number;
  in_transit: number;
  damaged: number;
  under_repair: number;
  awaiting_return: number;
  available: number;
  low_stock_threshold: number;
}

export interface InventoryLocation {
  id: string;
  name: string;
  building: string;
  items_count: number;
}

export interface InventoryTransfer {
  id: string;
  item_id: string;
  item_name: string;
  quantity: number;
  from_location_id: string;
  from_location_name: string;
  to_location_id: string;
  to_location_name: string;
  vehicle: string;
  status: "IN_TRANSIT" | "COMPLETED";
  eta: string;
  minutes_remaining: number;
}

export interface InventoryMovement {
  id: string;
  item_id: string;
  item_name: string;
  movement_type: "RECEIVE" | "RESERVE" | "RELEASE" | "TRANSFER_OUT" | "TRANSFER_IN" | "ISSUE" | "RETURN" | "DAMAGE" | "SEND_REPAIR" | "REPAIR_DONE" | "ADJUST";
  from_location: string | null;
  to_location: string | null;
  quantity: number;
  actor: string;
  reason: string;
  created_at: string;
}

export interface EquipmentFeasibility {
  item_name: string;
  venue_id: string;
  quantity_needed: number;
  available_on_site: {
    item_id: string;
    location_id: string;
    available_units: number;
  }[];
  transfer_needed: {
    item_id: string;
    source_location_id: string;
    source_location_name: string;
    available_units: number;
    travel_time_min: number;
    transfer_duration_min: number;
    feasible: boolean;
    latest_departure: string;
  }[];
  shortage: number;
}

export interface ReconciliationFlag {
  code: string;
  item: string;
  needed?: number;
  available_good?: number;
  total_under_repair?: number;
  location?: string;
  quantity?: number;
  condition?: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  message: string;
  action_label: string;
}
