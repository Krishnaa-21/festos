import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  Utensils,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileCheck,
  Building,
  PowerOff,
  AlertCircle,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  DietaryCoverageResponse,
  VendorItem,
  VendorComplianceData,
  ShutdownImpactResponse,
} from "./types";

export const FoodVendorsWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"matrix" | "compliance" | "vendors">("matrix");
  const [selectedVenueId, setSelectedVenueId] = useState<string>("V04");
  const [selectedMealSlot, setSelectedMealSlot] = useState<string>("LUNCH");

  // Vendor Shutdown Modal State
  const [shutdownVendorTarget, setShutdownVendorTarget] = useState<VendorItem | null>(null);
  const [selectedReplacementId, setSelectedReplacementId] = useState<string>("");
  const [shutdownReason, setShutdownReason] = useState("");
  const [approveNotifications, setApproveNotifications] = useState(true);

  const { addToast } = useToast();
  const showToast = (title: string, type: "success" | "warning" | "error" | "info" = "info") =>
    addToast({ title, type });
  const queryClient = useQueryClient();

  // Queries
  const { data: coverageData, isLoading: coverageLoading } = useQuery<DietaryCoverageResponse>({
    queryKey: ["food_coverage"],
    queryFn: async () => {
      const res = await api.get<DietaryCoverageResponse>("/api/v1/food/coverage");
      return res;
    },
  });

  const { data: vendorsList } = useQuery<VendorItem[]>({
    queryKey: ["vendors_list"],
    queryFn: async () => {
      const res = await api.get<{ items: VendorItem[]; total: number }>("/api/v1/vendors");
      return res?.items || [];
    },
  });

  const { data: complianceData } = useQuery<VendorComplianceData>({
    queryKey: ["vendors_compliance"],
    queryFn: async () => {
      const res = await api.get<VendorComplianceData>("/api/v1/vendors/compliance");
      return res;
    },
  });

  // Query shutdown impact simulation when target is selected
  const { data: shutdownImpact, isLoading: impactLoading } = useQuery<ShutdownImpactResponse | null>({
    queryKey: ["vendor_shutdown_impact", shutdownVendorTarget?.id],
    queryFn: async () => {
      if (!shutdownVendorTarget) return null;
      const res = await api.post<ShutdownImpactResponse>(`/api/v1/vendors/${shutdownVendorTarget.id}/shutdown-impact`);
      return res;
    },
    enabled: !!shutdownVendorTarget,
  });

  // Auto-select #1 ranked replacement vendor
  React.useEffect(() => {
    if (shutdownImpact?.ranked_replacements?.length && !selectedReplacementId) {
      setSelectedReplacementId(shutdownImpact.ranked_replacements[0].vendor_id);
    }
  }, [shutdownImpact, selectedReplacementId]);

  // Execute shutdown mutation
  const shutdownMutation = useMutation({
    mutationFn: async ({
      vendorId,
      replacementId,
      reason,
      dispatchNotes,
    }: {
      vendorId: string;
      replacementId: string;
      reason: string;
      dispatchNotes: boolean;
    }) => {
      return api.post(`/api/v1/vendors/${vendorId}/shutdown`, {
        replacement_vendor_id: replacementId,
        reason,
        dispatch_notifications: dispatchNotes,
      });
    },
    onSuccess: () => {
      showToast("Vendor emergency shutdown applied & replacement assigned", "success");
      setShutdownVendorTarget(null);
      setShutdownReason("");
      queryClient.invalidateQueries({ queryKey: ["vendors_list"] });
      queryClient.invalidateQueries({ queryKey: ["food_coverage"] });
    },
    onError: (err: any) => {
      showToast(err?.message || "Failed to execute shutdown", "error");
    },
  });

  // Matrix lookup helper
  const getMatrixCell = (category: string, mealSlot: string, venueId: string) => {
    return coverageData?.matrix.find(
      (m) => m.category === category && m.meal_slot === mealSlot && m.venue_id === venueId
    );
  };

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Utensils className="h-7 w-7 text-indigo-400" />
              Vendors & Food Operations
            </h1>
            <Badge variant="outline" className="font-mono text-xs">
              Dietary Coverage & Compliance
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Heat grid dietary coverage, certificate expiry timelines, menu-label mismatch audits, and emergency shutdowns
          </p>
        </div>

        {coverageData?.summary && coverageData.summary.zero_coverage_count > 0 && (
          <div className="flex items-center gap-2 rounded-lg bg-rose-950/40 border border-rose-500/40 px-3 py-1.5 text-xs text-rose-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{coverageData.summary.zero_coverage_count} zero-coverage cells detected</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2 overflow-x-auto pb-1">
        {[
          { id: "matrix", label: "Dietary Coverage Matrix", icon: Utensils, badge: coverageData?.summary.zero_coverage_count, badgeVariant: "danger" },
          { id: "compliance", label: "Certificates & Mismatches", icon: FileCheck, badge: complianceData?.mismatches.length, badgeVariant: "warning" },
          { id: "vendors", label: "Vendors & Commercial Rates", icon: Building, badge: vendorsList?.length },
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
              {tab.badge !== undefined && tab.badge > 0 && (
                <span
                  className={`ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full ${
                    tab.badgeVariant === "danger"
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                      : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: DIETARY COVERAGE MATRIX (HEAT GRID) */}
      {activeTab === "matrix" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Utensils className="h-5 w-5 text-indigo-400" />
                Dietary Coverage Matrix (Category x Meal Slot x Venue)
              </h2>
              <p className="text-xs text-slate-400">
                Zero-coverage cells are highlighted with direct action buttons. Every venue must provide certified options for all dietary requirements.
              </p>
            </div>

            {/* Filter controls */}
            <div className="flex items-center gap-2">
              <select
                aria-label="Filter by venue"
                value={selectedVenueId}
                onChange={(e) => setSelectedVenueId(e.target.value)}
                className="bg-[#0A0F1D] border border-slate-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                {coverageData?.venues.map((v) => (
                  <option key={v.id} value={v.id}>
                    Venue: {v.name} ({v.id})
                  </option>
                ))}
              </select>

              <select
                aria-label="Filter by meal slot"
                value={selectedMealSlot}
                onChange={(e) => setSelectedMealSlot(e.target.value)}
                className="bg-[#0A0F1D] border border-slate-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                {coverageData?.meal_slots.map((s) => (
                  <option key={s} value={s}>
                    Slot: {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Matrix Heat Grid Table */}
          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Dietary Category</th>
                    <th className="px-4 py-3">Capacity vs Demand</th>
                    <th className="px-4 py-3">Coverage Status</th>
                    <th className="px-4 py-3">Assigned Vendors</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {coverageLoading ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500">
                        Loading dietary coverage matrix...
                      </td>
                    </tr>
                  ) : (
                    coverageData?.categories.map((cat) => {
                      const cell = getMatrixCell(cat, selectedMealSlot, selectedVenueId);
                      const isZero = cell ? cell.is_zero_coverage : false;
                      const capacity = cell?.capacity || 0;
                      const demand = cell?.demand || 0;
                      const deficit = cell?.deficit || 0;

                      return (
                        <tr
                          key={cat}
                          className={`transition-colors ${
                            isZero
                              ? "bg-rose-950/20 hover:bg-rose-950/30"
                              : "hover:bg-slate-900/40"
                          }`}
                        >
                          <td className="px-4 py-3 font-semibold text-white">
                            <span className="font-mono text-sm">{cat}</span>
                          </td>

                          <td className="px-4 py-3 font-mono">
                            <div className="flex items-center gap-2">
                              <span>
                                Cap: <strong className={capacity === 0 ? "text-rose-400" : "text-white"}>{capacity}</strong>
                              </span>
                              <span>/</span>
                              <span>
                                Dem: <strong className="text-slate-300">{demand}</strong>
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3">
                            {isZero ? (
                              <span className="inline-flex items-center gap-1.5 rounded-lg bg-rose-950/80 border border-rose-500/60 px-2.5 py-1 text-xs font-bold text-rose-300 animate-pulse">
                                <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                                ZERO COVERAGE (Deficit: {deficit})
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 px-2.5 py-1 text-xs font-semibold text-emerald-300">
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                                FULL COVERAGE
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-3 text-slate-400 text-xs">
                            {cell?.vendor_names && cell.vendor_names.length > 0 ? (
                              cell.vendor_names.join(", ")
                            ) : (
                              <span className="italic text-rose-400 font-semibold">No vendor assigned</span>
                            )}
                          </td>

                          <td className="px-4 py-3 text-right">
                            <Button
                              size="sm"
                              variant={isZero ? "danger" : "secondary"}
                              onClick={() => {
                                showToast(`Assigning vendor for ${cat} in ${selectedMealSlot}`, "info");
                              }}
                              className="text-xs"
                            >
                              {isZero ? "Assign Vendor Immediately" : "Adjust Allocation"}
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

      {/* TAB 2: COMPLIANCE & MENU MISMATCHES */}
      {activeTab === "compliance" && (
        <div className="space-y-6">
          {/* Menu-Label Mismatches */}
          {complianceData?.mismatches && complianceData.mismatches.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-rose-400" />
                Menu-Label Mismatch Flags (Ingredient Discrepancies)
              </h2>

              <div className="space-y-3">
                {complianceData.mismatches.map((m) => (
                  <div
                    key={m.id}
                    className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-sm">{m.vendor_name}</span>
                        <span className="rounded bg-rose-950 text-rose-300 border border-rose-500/40 px-2 py-0.5 text-xs font-bold">
                          {m.severity} MISMATCH
                        </span>
                        <span className="text-xs font-semibold text-rose-300">Item: {m.item_name}</span>
                      </div>
                      <p className="text-xs text-slate-300">{m.issue}</p>
                    </div>

                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => showToast(`Audit ticket opened for ${m.vendor_name}`, "info")}
                      className="text-xs font-semibold shrink-0"
                    >
                      Audit / Fix Menu Label
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Certificate Expiry Timeline Table */}
          <div className="space-y-3 pt-2">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-emerald-400" />
              Hygiene Certification Expiry Timeline
            </h2>

            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                    <tr>
                      <th className="px-4 py-3">Vendor</th>
                      <th className="px-4 py-3">Certificate Type</th>
                      <th className="px-4 py-3">Certificate Number</th>
                      <th className="px-4 py-3">Valid Until</th>
                      <th className="px-4 py-3">Days Remaining</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans">
                    {complianceData?.certifications.map((c) => (
                      <tr key={c.certificate_number} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3 font-semibold text-white">{c.vendor_name}</td>
                        <td className="px-4 py-3 text-slate-300">{c.certificate_type}</td>
                        <td className="px-4 py-3 font-mono text-slate-400">{c.certificate_number}</td>
                        <td className="px-4 py-3 font-mono text-slate-300">{c.valid_until}</td>
                        <td className="px-4 py-3 font-mono font-bold">
                          <span
                            className={
                              c.days_left <= 2
                                ? "text-rose-400 font-extrabold"
                                : c.days_left <= 7
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }
                          >
                            {c.days_left} days
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                              c.status === "CRITICAL_EXPIRING"
                                ? "bg-rose-950 text-rose-300 border-rose-500/40"
                                : c.status === "WARNING_EXPIRING"
                                ? "bg-amber-950 text-amber-300 border-amber-500/40"
                                : "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                            }`}
                          >
                            {c.status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => showToast(`Requested certificate renewal for ${c.vendor_name}`, "info")}
                            className="text-xs"
                          >
                            Request Renewal
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: VENDORS DETAIL & EMERGENCY SHUTDOWN */}
      {activeTab === "vendors" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Building className="h-5 w-5 text-indigo-400" />
                Vendor Directory & Commercial Rates
              </h2>
              <p className="text-xs text-slate-400">
                Minimum guarantee commercial terms, capacity limits, and emergency shutdown workflows.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {vendorsList?.map((vendor) => (
              <div
                key={vendor.id}
                className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-base">{vendor.name}</span>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-bold border ${
                        vendor.status === "ACTIVE"
                          ? "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                          : "bg-rose-950 text-rose-300 border-rose-500/40"
                      }`}
                    >
                      {vendor.status}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 font-medium">{vendor.menu_description}</p>

                  <div className="text-xs text-slate-400 space-y-1 font-mono pt-1">
                    <div>Capacity: <strong className="text-white">{vendor.capacity} meals/slot</strong></div>
                    <div>Operating Hours: {vendor.hours}</div>
                    <div>Terms: {vendor.payment_terms.replace(/_/g, " ")}</div>
                    <div>Rate: <strong className="text-emerald-400">₹{vendor.base_rate_per_meal_inr} / meal</strong></div>
                  </div>
                </div>

                <div className="border-t border-slate-800/60 pt-3">
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => {
                      setShutdownVendorTarget(vendor);
                      setSelectedReplacementId("vnd_05");
                      setShutdownReason("");
                    }}
                    className="w-full text-xs font-bold flex items-center justify-center gap-1.5"
                  >
                    <PowerOff className="h-3.5 w-3.5" />
                    <span>Emergency Shutdown</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* EMERGENCY SHUTDOWN MODAL */}
      {shutdownVendorTarget && (
        <Modal
          isOpen={!!shutdownVendorTarget}
          onClose={() => setShutdownVendorTarget(null)}
          title={`Emergency Vendor Shutdown: ${shutdownVendorTarget.name}`}
          size="lg"
        >
          <div className="space-y-4 text-xs text-slate-300 font-sans">
            {/* Warning Alert */}
            <div className="rounded-lg bg-rose-950/40 border border-rose-500/40 p-3 flex items-start gap-2.5 text-rose-200">
              <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong>High-Risk Operational Mutation:</strong> Shutting down this vendor revokes their food license,
                reassigns meal slots, and calculates cost delta.
              </div>
            </div>

            {impactLoading ? (
              <div className="p-8 text-center text-slate-400">Simulating shutdown impact...</div>
            ) : shutdownImpact ? (
              <div className="space-y-4">
                {/* 1. Lost Capacity Summary */}
                <div className="grid grid-cols-2 gap-3 bg-slate-900 border border-slate-800 rounded-lg p-3">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Lost Capacity</span>
                    <strong className="text-rose-400 text-lg font-mono">
                      -{shutdownImpact.lost_capacity} meals / slot
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Estimated Cost Delta</span>
                    <strong className="text-amber-400 text-lg font-mono">
                      +{shutdownImpact.cost_delta_inr.toLocaleString()} INR
                    </strong>
                  </div>
                </div>

                {/* 2. Ranked Replacements Table */}
                <div className="space-y-2">
                  <div className="font-bold text-white text-xs uppercase tracking-wider">
                    Ranked Replacement Vendors (Capacity & Dietary Match)
                  </div>
                  <div className="rounded-lg border border-slate-800 overflow-hidden">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-slate-900 text-[10px] font-bold uppercase text-slate-400">
                        <tr>
                          <th className="p-2">Rank</th>
                          <th className="p-2">Vendor</th>
                          <th className="p-2">Available Capacity</th>
                          <th className="p-2">Dietary Match</th>
                          <th className="p-2">Cost Delta</th>
                          <th className="p-2 text-right">Select</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        {shutdownImpact.ranked_replacements.map((r) => (
                          <tr
                            key={r.vendor_id}
                            className={`hover:bg-slate-900/60 transition-colors ${
                              selectedReplacementId === r.vendor_id ? "bg-indigo-950/30 font-bold" : ""
                            }`}
                          >
                            <td className="p-2 text-indigo-400">#{r.rank}</td>
                            <td className="p-2 font-sans text-white">{r.vendor_name}</td>
                            <td className="p-2">{r.available_capacity} meals</td>
                            <td className="p-2 font-sans text-[11px] text-slate-300">{r.dietary_match}</td>
                            <td className="p-2 text-amber-300">
                              {r.cost_delta_inr >= 0 ? `+₹${r.cost_delta_inr}` : `-₹${Math.abs(r.cost_delta_inr)}`}
                            </td>
                            <td className="p-2 text-right font-sans">
                              <input
                                type="radio"
                                name="replacement_vendor"
                                checked={selectedReplacementId === r.vendor_id}
                                onChange={() => setSelectedReplacementId(r.vendor_id)}
                                className="text-indigo-600 focus:ring-0"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 3. Notification Drafts for Approval */}
                <div className="space-y-2">
                  <div className="font-bold text-white text-xs uppercase tracking-wider flex items-center justify-between">
                    <span>Notification Drafts for Approval</span>
                    <label className="flex items-center gap-1.5 text-xs text-indigo-300 font-normal cursor-pointer">
                      <input
                        type="checkbox"
                        checked={approveNotifications}
                        onChange={(e) => setApproveNotifications(e.target.checked)}
                        className="rounded border-slate-700 bg-slate-900 text-indigo-600"
                      />
                      <span>Approve & Dispatch Notifications</span>
                    </label>
                  </div>

                  <div className="space-y-2">
                    {shutdownImpact.notification_drafts.map((n) => (
                      <div key={n.id} className="rounded-lg bg-slate-900/70 border border-slate-800 p-2.5 text-xs space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                          <span>Channel: {n.channel}</span>
                          <span>Recipient: {n.recipient_group}</span>
                        </div>
                        <p className="text-slate-200">{n.body}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 4. Mandatory Reason Input */}
                <div>
                  <label className="block text-slate-400 mb-1 font-bold">
                    Mandatory Justification for Vendor Shutdown
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Enter reason for shutting down this vendor (e.g. hygiene failure, contamination breach)..."
                    value={shutdownReason}
                    onChange={(e) => setShutdownReason(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-white"
                  />
                </div>
              </div>
            ) : null}

            <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
              <Button variant="secondary" onClick={() => setShutdownVendorTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={!shutdownReason.trim() || !selectedReplacementId || shutdownMutation.isPending}
                onClick={() =>
                  shutdownMutation.mutate({
                    vendorId: shutdownVendorTarget.id,
                    replacementId: selectedReplacementId,
                    reason: shutdownReason,
                    dispatchNotes: approveNotifications,
                  })
                }
              >
                {shutdownMutation.isPending ? "Executing Shutdown..." : "Confirm Shutdown & Reassign"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default FoodVendorsWorkspace;
