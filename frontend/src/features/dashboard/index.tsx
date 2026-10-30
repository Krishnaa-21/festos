import React from "react";
import { FeatureDefinition } from "../../app/registry";

const DashboardOverview: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">FestOS Command Centre</h1>
        <p className="text-sm text-slate-400 mt-1">
          Aarohan Fest 2026 (EPINOIA, IIM Indore) — Operational Overview & Foundation Readiness
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 shadow-sm">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Raw Participants</div>
          <div className="text-3xl font-extrabold text-white mt-2">2,836</div>
          <div className="text-xs text-amber-400 mt-1 flex items-center">
            Reconciliation required vs 2,400 narrative
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 shadow-sm">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Contingents</div>
          <div className="text-3xl font-extrabold text-white mt-2">38</div>
          <div className="text-xs text-emerald-400 mt-1">All contingents registered</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 shadow-sm">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Campus Rooms / Beds</div>
          <div className="text-3xl font-extrabold text-white mt-2">200 / 710</div>
          <div className="text-xs text-slate-400 mt-1">+ 6 External Properties (740 beds)</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#111827] p-5 shadow-sm">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Scheduled Events</div>
          <div className="text-3xl font-extrabold text-white mt-2">31</div>
          <div className="text-xs text-indigo-400 mt-1">9 Campus Venues configured</div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-[#111827] p-6 shadow-sm">
        <h2 className="text-base font-semibold text-white">Platform Principles & Architecture</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-300 list-disc list-inside">
          <li><strong>ChangeService</strong>: Every mutation flows through transactional validation, snapshots, and audit logging.</li>
          <li><strong>Strict Ownership</strong>: P1 (Core & Schedule), P2 (Accommodation & Vendors), P3 (Auth & Audit).</li>
          <li><strong>First-class UNKNOWN</strong>: Missing data is never coerced to False, empty, or default consent.</li>
          <li><strong>Scenario Isolation</strong>: Real-time simulation runs in dedicated sandbox databases without affecting live data.</li>
        </ul>
      </div>
    </div>
  );
};

export const dashboardFeature: FeatureDefinition = {
  id: "dashboard",
  label: "Executive Dashboard",
  group: "Overview",
  path: "/dashboard",
  routes: [
    {
      path: "",
      element: <DashboardOverview />,
    },
  ],
};

export default dashboardFeature;
