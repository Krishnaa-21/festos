import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  DollarSign,
  AlertTriangle,
  Hotel,
  Receipt,
  ShoppingBag,
  Flame,
  ShieldCheck,
  Info,
  AlertCircle,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  FinanceSummary,
  AccommodationSpendProperty,
  VendorSettlement,
  MerchandiseCostItem,
  EmergencySpendItem,
  BudgetOverrideItem,
} from "./types";

export const FinanceWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "overview" | "accommodation" | "settlements" | "merchandise" | "emergency" | "overrides"
  >("overview");

  const [disputeModalTarget, setDisputeModalTarget] = useState<VendorSettlement | null>(null);

  const { addToast } = useToast();
  const showToast = (title: string, type: "success" | "warning" | "error" | "info" = "info") =>
    addToast({ title, type });

  // Queries
  const { data: summary } = useQuery<FinanceSummary>({
    queryKey: ["finance_summary"],
    queryFn: async () => {
      const res = await api.get<FinanceSummary>("/api/v1/finance/summary");
      return res;
    },
  });

  const { data: accomSpend, isLoading: accomLoading } = useQuery<{
    properties: AccommodationSpendProperty[];
    total_external_spend_inr: number;
  }>({
    queryKey: ["finance_accom_spend"],
    queryFn: async () => {
      const res = await api.get<{ properties: AccommodationSpendProperty[]; total_external_spend_inr: number }>(
        "/api/v1/finance/accommodation-spend"
      );
      return res;
    },
  });

  const { data: settlementsData, isLoading: settlementsLoading } = useQuery<{
    settlements: VendorSettlement[];
    total_payable_inr: number;
    disputed_amount_inr: number;
  }>({
    queryKey: ["finance_vendor_settlements"],
    queryFn: async () => {
      const res = await api.get<{ settlements: VendorSettlement[]; total_payable_inr: number; disputed_amount_inr: number }>(
        "/api/v1/finance/vendor-settlements"
      );
      return res;
    },
  });

  const { data: merchCosts, isLoading: merchLoading } = useQuery<{
    items: MerchandiseCostItem[];
    total_merchandise_spend_inr: number;
  }>({
    queryKey: ["finance_merchandise_costs"],
    queryFn: async () => {
      const res = await api.get<{ items: MerchandiseCostItem[]; total_merchandise_spend_inr: number }>(
        "/api/v1/finance/merchandise-costs"
      );
      return res;
    },
  });

  const { data: emergencySpend } = useQuery<{
    items: EmergencySpendItem[];
    total_emergency_spend_inr: number;
  }>({
    queryKey: ["finance_emergency_spend"],
    queryFn: async () => {
      const res = await api.get<{ items: EmergencySpendItem[]; total_emergency_spend_inr: number }>(
        "/api/v1/finance/emergency-spend"
      );
      return res;
    },
  });

  const { data: overridesData } = useQuery<BudgetOverrideItem[]>({
    queryKey: ["finance_overrides_report"],
    queryFn: async () => {
      const res = await api.get<{ overrides: BudgetOverrideItem[] }>("/api/v1/finance/overrides-report");
      return res?.overrides || [];
    },
  });

  const disputedSettlements = settlementsData?.settlements.filter((s) => s.status === "DISPUTED") || [];

  return (
    <div className="space-y-6 p-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <DollarSign className="h-7 w-7 text-emerald-400" />
              Finance & Commercial Operations
            </h1>
            <Badge variant="outline" className="font-mono text-xs">
              Commercial Ledgers
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Budget gauge, external property spends, vendor settlements, emergency disbursements, and override audit reports
          </p>
        </div>

        {summary?.external_budget_inr === null && (
          <div className="flex items-center gap-2 rounded-lg bg-amber-950/40 border border-amber-500/40 px-3 py-1.5 text-xs text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>external_budget_inr = NULL (Budget-Unset Mode)</span>
          </div>
        )}
      </div>

      {/* BUDGET-UNSET EXPLANATORY BANNER */}
      {summary?.external_budget_inr === null && (
        <div className="rounded-xl border border-amber-500/50 bg-amber-950/20 p-4 flex items-start gap-3 text-amber-200">
          <Info className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <div className="font-bold text-white text-sm">Operating in Budget-Unset Mode</div>
            <p className="text-slate-300">{summary.budget_explanation}</p>
            <div className="pt-1 flex items-center gap-3">
              <span className="font-semibold text-amber-300">
                Action required: Festival Director must set external accommodation ceiling in Assumptions Register.
              </span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => showToast("Navigating to Assumptions Register to propose budget limit", "info")}
                className="text-[11px] text-amber-300 hover:text-white"
              >
                Propose Budget Limit
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2 overflow-x-auto pb-1">
        {[
          { id: "overview", label: "Budget Gauge", icon: DollarSign },
          { id: "accommodation", label: "Accommodation Spend", icon: Hotel, badge: accomSpend?.properties.length },
          { id: "settlements", label: "Vendor Settlements", icon: Receipt, badge: disputedSettlements.length, badgeVariant: "danger" },
          { id: "merchandise", label: "Merchandise Costs", icon: ShoppingBag },
          { id: "emergency", label: "Emergency Spend", icon: Flame, badge: emergencySpend?.items.length },
          { id: "overrides", label: "Budget-Override Report", icon: ShieldCheck, badge: overridesData?.length },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-t-lg transition-all border-b-2 ${
                isActive
                  ? "border-emerald-500 text-emerald-400 bg-slate-900/60"
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
                      : "bg-slate-800 text-slate-300"
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ========================================================
          TAB 1: BUDGET GAUGE & OVERVIEW
         ======================================================== */}
      {activeTab === "overview" && summary && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-2">
              <span className="text-xs uppercase font-bold text-slate-400 block">External Budget Ceiling</span>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-mono font-extrabold text-amber-400">UNSET (NULL)</span>
                <span className="rounded bg-amber-950 text-amber-300 border border-amber-600/40 px-2 py-0.5 text-xs font-bold">
                  NO CEILING
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Demand-driven unconstrained calculation</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-2">
              <span className="text-xs uppercase font-bold text-slate-400 block">Total Spend Committed</span>
              <div className="text-2xl font-mono font-extrabold text-white">
                ₹{summary.total_spend_committed_inr.toLocaleString()}
              </div>
              <p className="text-[11px] text-emerald-400">Signed contracts & active bookings</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-2">
              <span className="text-xs uppercase font-bold text-slate-400 block">Total Spend Projected</span>
              <div className="text-2xl font-mono font-extrabold text-slate-300">
                ₹{summary.total_spend_projected_inr.toLocaleString()}
              </div>
              <p className="text-[11px] text-slate-400">Includes buffer & unplaced contingencies</p>
            </div>
          </div>

          {/* Category Breakdown Bars */}
          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-5 space-y-4">
            <h2 className="text-base font-bold text-white">Committed Spend Breakdown by Operational Area</h2>

            <div className="space-y-3 font-sans text-xs">
              {[
                {
                  label: "External Accommodation",
                  amount: summary.breakdown.external_accommodation_inr,
                  pct: Math.round((summary.breakdown.external_accommodation_inr / summary.total_spend_committed_inr) * 100),
                  color: "bg-indigo-500",
                },
                {
                  label: "Vendors & Catering",
                  amount: summary.breakdown.vendors_and_catering_inr,
                  pct: Math.round((summary.breakdown.vendors_and_catering_inr / summary.total_spend_committed_inr) * 100),
                  color: "bg-emerald-500",
                },
                {
                  label: "Merchandise & Credentials",
                  amount: summary.breakdown.merchandise_inr,
                  pct: Math.round((summary.breakdown.merchandise_inr / summary.total_spend_committed_inr) * 100),
                  color: "bg-amber-500",
                },
                {
                  label: "Logistics & Equipment Rigging",
                  amount: summary.breakdown.logistics_equipment_inr,
                  pct: Math.round((summary.breakdown.logistics_equipment_inr / summary.total_spend_committed_inr) * 100),
                  color: "bg-cyan-500",
                },
                {
                  label: "Approved Emergency Spend",
                  amount: summary.breakdown.approved_emergency_inr,
                  pct: Math.round((summary.breakdown.approved_emergency_inr / summary.total_spend_committed_inr) * 100),
                  color: "bg-rose-500",
                },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-slate-300">
                    <span className="font-medium text-white">{item.label}</span>
                    <span className="font-mono">
                      ₹{item.amount.toLocaleString()} ({item.pct}%)
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          TAB 2: EXTERNAL ACCOMMODATION SPEND
         ======================================================== */}
      {activeTab === "accommodation" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Hotel className="h-5 w-5 text-indigo-400" />
                External Accommodation Spend by Property
              </h2>
              <p className="text-xs text-slate-400">
                Tracking 6 external properties booked to cover campus hostel overflow.
              </p>
            </div>
            <div className="font-mono text-xs text-slate-300">
              Total External Spend:{" "}
              <strong className="text-white text-sm">
                ₹{accomSpend?.total_external_spend_inr.toLocaleString()}
              </strong>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Property</th>
                    <th className="px-4 py-3">Capacity / Booked</th>
                    <th className="px-4 py-3">Nights</th>
                    <th className="px-4 py-3 text-right">Rate / Bed-Night</th>
                    <th className="px-4 py-3 text-right">Total Spend (INR)</th>
                    <th className="px-4 py-3">Contract Status</th>
                    <th className="px-4 py-3">Payment Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {accomLoading ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        Loading accommodation spend...
                      </td>
                    </tr>
                  ) : (
                    accomSpend?.properties.map((p) => (
                      <tr key={p.property_id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{p.name}</div>
                          <div className="font-mono text-[10px] text-slate-500">{p.property_id}</div>
                        </td>
                        <td className="px-4 py-3 font-mono">
                          {p.booked_beds} / {p.capacity_beds} beds
                        </td>
                        <td className="px-4 py-3 font-mono">{p.nights} nights</td>
                        <td className="px-4 py-3 font-mono text-right text-slate-200">
                          ₹{p.rate_per_bed_night_inr.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 font-mono text-right font-bold text-white">
                          ₹{p.total_spend_inr.toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant="outline">{p.contract_status}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-bold border ${
                              p.payment_status === "ADVANCE_PAID"
                                ? "bg-emerald-950 text-emerald-300 border-emerald-500/40"
                                : "bg-amber-950 text-amber-300 border-amber-500/40"
                            }`}
                          >
                            {p.payment_status}
                          </span>
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

      {/* ========================================================
          TAB 3: VENDOR SETTLEMENTS & DISPUTES
         ======================================================== */}
      {activeTab === "settlements" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Receipt className="h-5 w-5 text-indigo-400" />
                Vendor Commercial Settlements & Billing Disputes
              </h2>
              <p className="text-xs text-slate-400">
                Payment milestones, balances due, advance deduction, and active billing dispute audits.
              </p>
            </div>
            <div className="font-mono text-xs text-slate-300">
              Total Payable:{" "}
              <strong className="text-white">₹{settlementsData?.total_payable_inr.toLocaleString()}</strong>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Vendor</th>
                    <th className="px-4 py-3 text-right">Contract Total</th>
                    <th className="px-4 py-3 text-right">Advance Paid</th>
                    <th className="px-4 py-3 text-right">Balance Due</th>
                    <th className="px-4 py-3">Due Date</th>
                    <th className="px-4 py-3">Settlement Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {settlementsLoading ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500">
                        Loading settlements...
                      </td>
                    </tr>
                  ) : (
                    settlementsData?.settlements.map((s) => (
                      <tr key={s.vendor_id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{s.vendor_name}</div>
                          <div className="font-mono text-[10px] text-slate-500">{s.vendor_id}</div>
                        </td>
                        <td className="px-4 py-3 font-mono text-right">₹{s.contract_total_inr.toLocaleString()}</td>
                        <td className="px-4 py-3 font-mono text-right text-slate-400">
                          ₹{s.advance_paid_inr.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 font-mono text-right font-bold text-white">
                          ₹{s.balance_due_inr.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-300">{s.due_date}</td>
                        <td className="px-4 py-3">
                          {s.status === "DISPUTED" ? (
                            <span className="inline-flex items-center gap-1 rounded bg-rose-950/80 border border-rose-500/50 px-2 py-0.5 text-xs font-bold text-rose-300">
                              <AlertCircle className="h-3 w-3 text-rose-400 shrink-0" />
                              DISPUTED
                            </span>
                          ) : (
                            <Badge variant="outline">{s.status}</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {s.dispute ? (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => setDisputeModalTarget(s)}
                              className="text-xs font-semibold"
                            >
                              Review Dispute
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => showToast(`Payment processed for ${s.vendor_name}`, "success")}
                              className="text-xs"
                            >
                              Settle Invoice
                            </Button>
                          )}
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

      {/* DISPUTE REVIEW MODAL */}
      {disputeModalTarget && disputeModalTarget.dispute && (
        <Modal
          isOpen={!!disputeModalTarget}
          onClose={() => setDisputeModalTarget(null)}
          title={`Billing Dispute: ${disputeModalTarget.vendor_name}`}
        >
          <div className="space-y-4 text-xs text-slate-300">
            <div className="rounded-lg bg-rose-950/40 border border-rose-500/40 p-3 space-y-1 text-rose-200">
              <div className="font-bold text-sm text-white">Disputed Amount: ₹{disputeModalTarget.dispute.amount_inr.toLocaleString()}</div>
              <p>{disputeModalTarget.dispute.reason}</p>
              <div className="text-[10px] text-slate-400 pt-1">
                Opened by {disputeModalTarget.dispute.opened_by} at {disputeModalTarget.dispute.opened_at.slice(0, 16)}
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-800 pt-3">
              <Button variant="secondary" onClick={() => setDisputeModalTarget(null)}>
                Dismiss
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  showToast("Dispute resolved with settlement adjustment token", "success");
                  setDisputeModalTarget(null);
                }}
              >
                Approve Adjusted Settlement
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ========================================================
          TAB 4: MERCHANDISE PROCUREMENT COSTS
         ======================================================== */}
      {activeTab === "merchandise" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShoppingBag className="h-5 w-5 text-indigo-400" />
                Merchandise Procurement Expenditure
              </h2>
              <p className="text-xs text-slate-400">
                Supplier contracts, ordered quantities, unit costs, and total procurement spend.
              </p>
            </div>
            <div className="font-mono text-xs text-slate-300">
              Total Merch Spend:{" "}
              <strong className="text-white">₹{merchCosts?.total_merchandise_spend_inr.toLocaleString()}</strong>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-[#0A0F1D] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400 font-bold">
                  <tr>
                    <th className="px-4 py-3">Item</th>
                    <th className="px-4 py-3">Supplier</th>
                    <th className="px-4 py-3 text-right">Unit Cost</th>
                    <th className="px-4 py-3 text-right">Ordered Qty</th>
                    <th className="px-4 py-3 text-right font-bold text-white">Total Cost (INR)</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {merchLoading ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500">
                        Loading merchandise costs...
                      </td>
                    </tr>
                  ) : (
                    merchCosts?.items.map((it) => (
                      <tr key={it.item_name} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3 font-semibold text-white">{it.item_name}</td>
                        <td className="px-4 py-3 text-slate-300">{it.supplier}</td>
                        <td className="px-4 py-3 font-mono text-right">₹{it.unit_cost_inr}</td>
                        <td className="px-4 py-3 font-mono text-right">{it.ordered_qty}</td>
                        <td className="px-4 py-3 font-mono text-right font-bold text-emerald-400">
                          ₹{it.total_cost_inr.toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-xs font-bold">
                            {it.status}
                          </span>
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

      {/* ========================================================
          TAB 5: APPROVED EMERGENCY SPEND
         ======================================================== */}
      {activeTab === "emergency" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Flame className="h-5 w-5 text-rose-400" />
                Approved Emergency Disbursements
              </h2>
              <p className="text-xs text-slate-400">
                Unforeseen incident expenses authorized by the Festival Director with linked audit trails.
              </p>
            </div>
            <div className="font-mono text-xs text-slate-300">
              Total Emergency Spend:{" "}
              <strong className="text-rose-400">₹{emergencySpend?.total_emergency_spend_inr.toLocaleString()}</strong>
            </div>
          </div>

          <div className="space-y-3">
            {emergencySpend?.items.map((it) => (
              <div
                key={it.id}
                className="rounded-xl border border-rose-500/30 bg-[#0A0F1D] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{it.description}</span>
                    <span className="rounded bg-rose-950 text-rose-300 border border-rose-500/40 px-2 py-0.5 text-xs font-bold">
                      EMERGENCY
                    </span>
                    <span className="font-mono text-xs font-bold text-emerald-400">
                      ₹{it.amount_inr.toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300">Reason: {it.reason}</p>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Approved by {it.approved_by} • {it.approved_at.slice(0, 16).replace("T", " ")}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => showToast(`Audit trail ${it.audit_link} verified`, "info")}
                    className="text-xs font-mono"
                  >
                    View Audit ({it.audit_link})
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================
          TAB 6: BUDGET-OVERRIDE REPORT
         ======================================================== */}
      {activeTab === "overrides" && (
        <div className="space-y-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-indigo-400" />
              Budget & Cost Overrides Register
            </h2>
            <p className="text-xs text-slate-400">
              Complete audit log of all financial constraints overridden during fest planning.
            </p>
          </div>

          <div className="space-y-3">
            {overridesData?.map((ovr) => (
              <div
                key={ovr.id}
                className="rounded-xl border border-slate-800 bg-[#0A0F1D] p-4 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white text-sm">{ovr.target_entity}</span>
                    <span className="rounded bg-amber-950 text-amber-300 border border-amber-600/40 px-2 py-0.5 text-xs font-bold">
                      {ovr.category}
                    </span>
                    <span className="font-mono text-xs text-slate-400">{ovr.id}</span>
                  </div>

                  <span className="font-mono font-bold text-amber-400 text-sm">
                    Delta: +₹{ovr.delta_inr.toLocaleString()}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Original Baseline</span>
                    <span className="text-slate-300 font-mono">{ovr.original_value}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Overridden Value</span>
                    <span className="text-white font-mono font-bold">{ovr.overridden_value}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-300">
                  <strong>Justification:</strong> {ovr.reason}
                </p>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800/60">
                  <span>
                    Authorized by <strong>{ovr.authorized_by}</strong> at {ovr.authorized_at.slice(0, 16)}
                  </span>
                  <span className="font-mono text-indigo-400">Audit ID: {ovr.audit_event_id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FinanceWorkspace;
