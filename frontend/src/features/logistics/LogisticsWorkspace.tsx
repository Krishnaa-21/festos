import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  Package,
  Truck,
  ArrowRightLeft,
  AlertTriangle,
  MapPin,
  Clock,
  Search,
  Camera,
  Layers,
  Wrench,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  StockItem,
  InventoryLocation,
  InventoryTransfer,
  InventoryMovement,
  EquipmentFeasibility,
  ReconciliationFlag,
} from "./types";

export const LogisticsWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"stock" | "transfers" | "movements" | "feasibility" | "reconciliation">("stock");
  const [searchTerm, setSearchTerm] = useState("");
  const [kindFilter, setKindFilter] = useState<string>("all");

  // Feasibility search inputs
  const [feasibilityItem, setFeasibilityItem] = useState("projector");
  const [feasibilityVenue, setFeasibilityVenue] = useState("V01");

  // Stocktake modal
  const [stocktakeTarget, setStocktakeTarget] = useState<StockItem | null>(null);
  const [countedQty, setCountedQty] = useState<number>(0);
  const [stocktakeReason, setStocktakeReason] = useState("");

  const { addToast } = useToast();
  const showToast = (title: string, type: "success" | "warning" | "error" | "info" = "info") =>
    addToast({ title, type });
  const queryClient = useQueryClient();

  // Queries
  const { data: stockItems, isLoading: stockLoading } = useQuery<StockItem[]>({
    queryKey: ["logistics_items"],
    queryFn: async () => {
      const res = await api.get<{ items: StockItem[]; total: number }>("/api/v1/logistics/items");
      return res?.items || [];
    },
  });

  const { data: locations } = useQuery<InventoryLocation[]>({
    queryKey: ["logistics_locations"],
    queryFn: async () => {
      const res = await api.get<{ locations: InventoryLocation[] }>("/api/v1/logistics/locations");
      return res?.locations || [];
    },
  });

  const { data: transfers, isLoading: transfersLoading } = useQuery<InventoryTransfer[]>({
    queryKey: ["logistics_transfers"],
    queryFn: async () => {
      const res = await api.get<{ transfers: InventoryTransfer[] }>("/api/v1/logistics/transfers");
      return res?.transfers || [];
    },
    refetchInterval: 10000,
  });

  const { data: movements, isLoading: movementsLoading } = useQuery<InventoryMovement[]>({
    queryKey: ["logistics_movements"],
    queryFn: async () => {
      const res = await api.get<{ items: InventoryMovement[] }>("/api/v1/logistics/movements");
      return res?.items || [];
    },
  });

  const { data: feasibilityData, isLoading: feasibilityLoading } = useQuery<EquipmentFeasibility>({
    queryKey: ["logistics_feasibility", feasibilityItem, feasibilityVenue],
    queryFn: async () => {
      const res = await api.get<EquipmentFeasibility>("/api/v1/logistics/equipment/find", {
        params: { item_name: feasibilityItem, venue_id: feasibilityVenue },
      });
      return res;
    },
  });

  const { data: reconciliationFlags } = useQuery<ReconciliationFlag[]>({
    queryKey: ["logistics_flags"],
    queryFn: async () => {
      const res = await api.get<{ flags: ReconciliationFlag[] }>("/api/v1/logistics/reconciliation-flags");
      return res?.flags || [];
    },
  });

  // Complete transfer mutation
  const completeTransferMutation = useMutation({
    mutationFn: async (transferId: string) => {
      return api.post(`/api/v1/logistics/transfers/${transferId}/complete`);
    },
    onSuccess: () => {
      showToast("Transfer marked completed (TRANSFER_IN executed)", "success");
      queryClient.invalidateQueries({ queryKey: ["logistics_transfers"] });
      queryClient.invalidateQueries({ queryKey: ["logistics_items"] });
    },
  });

  // Stocktake adjustment mutation
  const stocktakeMutation = useMutation({
    mutationFn: async ({ item, count, reason }: { item: StockItem; count: number; reason: string }) => {
      return api.post("/api/v1/logistics/stocktake", {
        item_id: item.id,
        counted_quantity: count,
        current_on_hand: item.on_hand,
        delta: count - item.on_hand,
        reason,
      });
    },
    onSuccess: () => {
      showToast("Stocktake discrepancy adjusted in ledger", "success");
      setStocktakeTarget(null);
      queryClient.invalidateQueries({ queryKey: ["logistics_items"] });
      queryClient.invalidateQueries({ queryKey: ["logistics_movements"] });
    },
  });

  // Filtered stock
  const filteredStock = (stockItems || []).filter((item) => {
    if (kindFilter !== "all" && item.kind !== kindFilter) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        item.name.toLowerCase().includes(q) ||
        item.code.toLowerCase().includes(q) ||
        item.location_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const lowStockCount = (stockItems || []).filter((i) => i.available <= i.low_stock_threshold).length;

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Package className="h-7 w-7 text-indigo-400" />
              Logistics & Equipment Operations
            </h1>
            <Badge variant="outline" className="font-mono text-xs">
              Double-Entry Ledger
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Time- and location-aware stock buckets, transfers, equipment assignment, and reconciliation flags
          </p>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-3">
          {lowStockCount > 0 && (
            <div className="flex items-center gap-1.5 rounded-lg bg-rose-950/40 border border-rose-500/40 px-3 py-1.5 text-xs text-rose-300">
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{lowStockCount} items at or below low-stock threshold</span>
            </div>
          )}
        </div>
      </div>

      {/* Reconciliation Alert Banner (Camera & Tables Cases) */}
      {reconciliationFlags && reconciliationFlags.length > 0 && (
        <div className="space-y-2">
          {reconciliationFlags.map((flag) => (
            <div
              key={flag.code}
              className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                flag.severity === "HIGH"
                  ? "border-rose-500/50 bg-rose-950/20 text-rose-200"
                  : "border-amber-500/50 bg-amber-950/20 text-amber-200"
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-rose-400" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-white">{flag.code}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        flag.severity === "HIGH"
                          ? "bg-rose-950 text-rose-300 border-rose-600/40"
                          : "bg-amber-950 text-amber-300 border-amber-600/40"
                      }`}
                    >
                      RECONCILIATION FLAG
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">{flag.message}</p>
                </div>
              </div>

              <Button
                variant={flag.severity === "HIGH" ? "danger" : "secondary"}
                size="sm"
                onClick={() => {
                  showToast(`Executing action: ${flag.action_label}`, "info");
                  if (flag.code === "CAMERA_ALL_UNDER_REPAIR") {
                    setActiveTab("stock");
                    setSearchTerm("camera");
                  } else if (flag.code === "TABLES_NEEDS_CHECK") {
                    setActiveTab("stock");
                    setSearchTerm("table");
                  }
                }}
                className="shrink-0 text-xs font-semibold"
              >
                {flag.action_label}
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2 overflow-x-auto pb-1">
        {[
          { id: "stock", label: "Stock Buckets (7 States)", icon: Layers, badge: stockItems?.length },
          { id: "transfers", label: "Locations & Transfers", icon: Truck, badge: transfers?.length },
          { id: "movements", label: "Movement Ledger", icon: ArrowRightLeft, badge: movements?.length },
          { id: "feasibility", label: "Session Assignment & Feasibility", icon: Clock },
          { id: "reconciliation", label: "Reconciliation Flags", icon: Wrench, badge: reconciliationFlags?.length },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-t-lg transition-all border-b-2 ${
                isActive
                  ? "border-indigo-500 text-indigo-400 bg-slate-900/60"
                  : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-300">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: STOCK BUCKETS TABLE */}
      {activeTab === "stock" && (
        <div className="space-y-4">
          {/* Filters & Search */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search item name, code, or location..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-[#0A0F1D] border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                aria-label="Filter by item kind"
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value)}
                className="bg-[#0A0F1D] border border-slate-800 text-xs text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Item Kinds</option>
                <option value="equipment">Equipment Only</option>
                <option value="merch">Merchandise Only</option>
              </select>
            </div>
          </div>

          {/* Stock Table */}
          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Item / Code</th>
                    <th className="px-4 py-3">Location</th>
                    <th className="px-3 py-3 text-right">On Hand</th>
                    <th className="px-3 py-3 text-right">Reserved</th>
                    <th className="px-3 py-3 text-right">In Transit</th>
                    <th className="px-3 py-3 text-right">Damaged</th>
                    <th className="px-3 py-3 text-right">Under Repair</th>
                    <th className="px-3 py-3 text-right">Awaiting Return</th>
                    <th className="px-3 py-3 text-right font-extrabold text-white">Available</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {stockLoading ? (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-slate-500">
                        Loading stock buckets...
                      </td>
                    </tr>
                  ) : filteredStock.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-slate-500">
                        No items match search filter.
                      </td>
                    </tr>
                  ) : (
                    filteredStock.map((item) => {
                      const isLowStock = item.available <= item.low_stock_threshold;
                      return (
                        <tr key={item.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="px-4 py-3 font-sans">
                            <div className="font-semibold text-white">{item.name}</div>
                            <div className="font-mono text-[10px] text-slate-500">{item.code}</div>
                          </td>
                          <td className="px-4 py-3 font-sans">
                            <div className="text-slate-300">{item.location_name}</div>
                            <div className="text-[10px] text-slate-500">{item.condition}</div>
                          </td>
                          <td className="px-3 py-3 text-right text-slate-200">{item.on_hand}</td>
                          <td className="px-3 py-3 text-right text-slate-400">{item.reserved}</td>
                          <td className="px-3 py-3 text-right text-indigo-400 font-bold">
                            {item.in_transit > 0 ? `+${item.in_transit}` : "0"}
                          </td>
                          <td className="px-3 py-3 text-right text-rose-400">{item.damaged}</td>
                          <td className="px-3 py-3 text-right text-amber-400 font-bold">{item.under_repair}</td>
                          <td className="px-3 py-3 text-right text-slate-400">{item.awaiting_return}</td>
                          <td className="px-3 py-3 text-right font-extrabold text-base">
                            <span
                              className={`px-2 py-0.5 rounded ${
                                isLowStock
                                  ? "bg-rose-950/60 text-rose-300 border border-rose-800/40"
                                  : "text-emerald-400"
                              }`}
                            >
                              {item.available}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-sans">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => {
                                setStocktakeTarget(item);
                                setCountedQty(item.on_hand);
                                setStocktakeReason("");
                              }}
                              className="text-[11px]"
                            >
                              Stocktake
                            </Button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: LOCATIONS & ACTIVE TRANSFERS */}
      {activeTab === "transfers" && (
        <div className="space-y-6">
          {/* Active Transfers */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Truck className="h-5 w-5 text-indigo-400" />
              Active Equipment Transfers (In-Transit Stock)
            </h2>
            <p className="text-xs text-slate-400">
              Double-entry rule: Stock in transit counts at neither source nor destination until explicitly received.
            </p>

            <div className="space-y-3">
              {transfersLoading ? (
                <div className="p-8 text-center text-slate-400">Loading transfers...</div>
              ) : transfers?.length === 0 ? (
                <div className="p-6 text-center text-slate-400 rounded-xl border border-slate-800 bg-[#0A0F1D]">
                  No active transfers in progress.
                </div>
              ) : (
                transfers?.map((trf) => (
                  <div
                    key={trf.id}
                    className="rounded-xl border border-indigo-500/30 bg-indigo-950/10 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{trf.item_name}</span>
                        <Badge variant="outline" className="font-mono text-xs">
                          Qty: {trf.quantity}
                        </Badge>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-600/40">
                          {trf.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-300">
                        <span>{trf.from_location_name}</span>
                        <ArrowRightLeft className="h-3 w-3 text-slate-500" />
                        <span className="font-semibold text-white">{trf.to_location_name}</span>
                        <span>•</span>
                        <span className="text-slate-400">Via {trf.vehicle}</span>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-indigo-300 pt-1">
                        <Clock className="h-3.5 w-3.5" />
                        <span>ETA: {trf.eta.slice(11, 16)}</span>
                        <span>({trf.minutes_remaining} minutes remaining)</span>
                      </div>
                    </div>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => completeTransferMutation.mutate(trf.id)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-xs shrink-0"
                    >
                      Mark Arrived (TRANSFER_IN)
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Locations Overview */}
          <div className="space-y-3 pt-4 border-t border-slate-800">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <MapPin className="h-5 w-5 text-emerald-400" />
              Campus Storage Locations
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {locations?.map((loc) => (
                <div key={loc.id} className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 space-y-2">
                  <div className="font-bold text-white text-sm">{loc.name}</div>
                  <div className="text-xs text-slate-400">{loc.building}</div>
                  <div className="text-xs font-mono text-indigo-400 font-semibold">{loc.items_count} items stored</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MOVEMENT LEDGER */}
      {activeTab === "movements" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ArrowRightLeft className="h-5 w-5 text-indigo-400" />
                Immutable Inventory Movements Ledger
              </h2>
              <p className="text-xs text-slate-400">
                Every quantity change is an audited movement record with mandatory justification.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Movement ID</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Item</th>
                    <th className="px-4 py-3">Quantity</th>
                    <th className="px-4 py-3">From / To</th>
                    <th className="px-4 py-3">Reason / Context</th>
                    <th className="px-4 py-3">Actor / Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {movementsLoading ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        Loading movements...
                      </td>
                    </tr>
                  ) : (
                    movements?.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3 font-bold text-slate-400">{m.id}</td>
                        <td className="px-4 py-3 font-sans">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                              m.movement_type === "DAMAGE"
                                ? "bg-rose-950/60 text-rose-300 border-rose-800/40"
                                : m.movement_type === "RECEIVE"
                                ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/40"
                                : "bg-indigo-950/60 text-indigo-300 border-indigo-800/40"
                            }`}
                          >
                            {m.movement_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-sans text-white">{m.item_name}</td>
                        <td className="px-4 py-3 font-bold text-slate-200">{m.quantity}</td>
                        <td className="px-4 py-3 font-sans text-xs text-slate-400">
                          {m.from_location || "None"} → {m.to_location || "None"}
                        </td>
                        <td className="px-4 py-3 font-sans text-xs text-slate-300 max-w-xs truncate">
                          {m.reason}
                        </td>
                        <td className="px-4 py-3 font-sans text-[11px] text-slate-500">
                          <div>{m.actor}</div>
                          <div>{m.created_at.slice(0, 16).replace("T", " ")}</div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: SESSION ASSIGNMENT & TRANSFER FEASIBILITY */}
      {activeTab === "feasibility" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="h-5 w-5 text-indigo-400" />
              Equipment Assignment & Transfer Feasibility Check
            </h2>
            <p className="text-xs text-slate-400">
              Evaluates if equipment can be transferred in time for a session (travel time + 15m transfer buffer).
            </p>
          </div>

          {/* Search Inputs */}
          <div className="flex flex-wrap gap-3 bg-[#0A0F1D] border border-slate-800 p-4 rounded-xl items-center">
            <div>
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Equipment Name</label>
              <input
                type="text"
                value={feasibilityItem}
                onChange={(e) => setFeasibilityItem(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-white rounded px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">Target Venue</label>
              <select
                aria-label="Target venue"
                value={feasibilityVenue}
                onChange={(e) => setFeasibilityVenue(e.target.value)}
                className="bg-slate-900 border border-slate-700 text-xs text-white rounded px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="V01">Main Auditorium (V01)</option>
                <option value="V02">Management Hall 1 (V02)</option>
                <option value="V04">Amphitheatre (V04)</option>
                <option value="V05">Sports Complex (V05)</option>
              </select>
            </div>
          </div>

          {/* Results */}
          {feasibilityLoading ? (
            <div className="p-8 text-center text-slate-400">Checking equipment feasibility...</div>
          ) : feasibilityData ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* On Site */}
              <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white text-sm">Available On-Site</h3>
                  <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-xs font-bold">
                    READY
                  </span>
                </div>
                {feasibilityData.available_on_site.map((u) => (
                  <div key={u.item_id} className="text-xs text-slate-300">
                    Location: {u.location_id} • Available Units: <strong>{u.available_units}</strong>
                  </div>
                ))}
              </div>

              {/* Transfer Candidate */}
              <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white text-sm">Transfer From Central Store</h3>
                  {feasibilityData.transfer_needed.some((t) => t.feasible) ? (
                    <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-xs font-bold">
                      FEASIBLE (Buffer Satisfied)
                    </span>
                  ) : (
                    <span className="rounded bg-rose-950 text-rose-300 border border-rose-500/40 px-2 py-0.5 text-xs font-bold">
                      INFEASIBLE (Buffer Breach)
                    </span>
                  )}
                </div>

                {feasibilityData.transfer_needed.map((t) => (
                  <div key={t.item_id} className="text-xs text-slate-300 space-y-1">
                    <div>Source: {t.source_location_name}</div>
                    <div>
                      Travel: {t.travel_time_min}m + Transfer Buffer: {t.transfer_duration_min}m
                    </div>
                    <div>Latest Departure: {t.latest_departure.slice(11, 16)}</div>
                    <div className="pt-2">
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => showToast(`Initiated transfer from ${t.source_location_name}`, "success")}
                        className="text-xs"
                      >
                        Initiate Transfer
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* TAB 5: RECONCILIATION FLAGS */}
      {activeTab === "reconciliation" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Wrench className="h-5 w-5 text-rose-400" />
              Reconciliation Flags (Transparent Diagnostics)
            </h2>
            <p className="text-xs text-slate-400">
              The camera and tables cases surface as reconciliation flags rather than unverified shortages.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Camera className="h-5 w-5 text-rose-400" />
                  <span className="font-bold text-white">The Camera Case</span>
                </div>
                <span className="rounded bg-rose-950 text-rose-300 border border-rose-600/50 px-2 py-0.5 text-xs font-bold">
                  HIGH SEVERITY
                </span>
              </div>

              <p className="text-xs text-slate-300">
                All 31 cameras across 4 locations are logged as <strong>under repair</strong>. Zero are available in
                good condition, but 3 are needed for scheduled media coverage sessions.
              </p>

              <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 text-xs text-slate-400 font-mono">
                <div>Needed: 3 units</div>
                <div>Available Good: 0 units</div>
                <div>Total Under Repair: 31 units</div>
              </div>

              <Button
                variant="danger"
                size="sm"
                onClick={() => showToast("Inspection team dispatched to evaluate camera batch", "success")}
                className="w-full text-xs font-semibold"
              >
                Inspect Cameras / Reconcile Status
              </Button>
            </div>

            <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers className="h-5 w-5 text-amber-400" />
                  <span className="font-bold text-white">The Tables Case</span>
                </div>
                <span className="rounded bg-amber-950 text-amber-300 border border-amber-600/50 px-2 py-0.5 text-xs font-bold">
                  MEDIUM SEVERITY
                </span>
              </div>

              <p className="text-xs text-slate-300">
                42 folding tables in Sports Complex are flagged as <strong>needs check</strong>. Physical integrity
                and leg stability are unverified before morning event setups.
              </p>

              <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 text-xs text-slate-400 font-mono">
                <div>Location: Sports Complex Ground</div>
                <div>Quantity: 42 units</div>
                <div>Condition: needs check (unverified)</div>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => showToast("Verification crew assigned to check folding tables", "success")}
                className="w-full text-xs font-semibold text-amber-300 hover:text-white"
              >
                Verify Physical Condition
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* STOCKTAKE MODAL */}
      {stocktakeTarget && (
        <Modal
          isOpen={!!stocktakeTarget}
          onClose={() => setStocktakeTarget(null)}
          title={`Stocktake Adjustment: ${stocktakeTarget.name}`}
        >
          <div className="space-y-4 text-xs text-slate-300">
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-1">
              <div>Location: {stocktakeTarget.location_name}</div>
              <div>Current On Hand: <strong className="text-white font-mono">{stocktakeTarget.on_hand}</strong></div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Physical Count Result</label>
              <input
                type="number"
                value={countedQty}
                onChange={(e) => setCountedQty(parseInt(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white font-mono text-base"
              />
              <div className="text-[11px] text-slate-400 mt-1">
                Discrepancy (Delta):{" "}
                <strong
                  className={
                    countedQty - stocktakeTarget.on_hand < 0
                      ? "text-rose-400"
                      : countedQty - stocktakeTarget.on_hand > 0
                      ? "text-emerald-400"
                      : "text-slate-400"
                  }
                >
                  {countedQty - stocktakeTarget.on_hand > 0 ? `+${countedQty - stocktakeTarget.on_hand}` : countedQty - stocktakeTarget.on_hand}
                </strong>
              </div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Mandatory Reason for Discrepancy</label>
              <textarea
                rows={3}
                placeholder="Explain the physical count variance (e.g. damaged stock discarded)..."
                value={stocktakeReason}
                onChange={(e) => setStocktakeReason(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-white"
              />
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
              <Button variant="secondary" onClick={() => setStocktakeTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                disabled={!stocktakeReason.trim()}
                onClick={() =>
                  stocktakeMutation.mutate({
                    item: stocktakeTarget,
                    count: countedQty,
                    reason: stocktakeReason,
                  })
                }
              >
                Apply Adjustment Movement
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default LogisticsWorkspace;
