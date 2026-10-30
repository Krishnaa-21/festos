import React, { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { NAV_GROUPS, getFeaturesByGroup } from "../../app/registry";
import {
  ChevronRight,
  Activity,
  Menu,
  X,
  Layers,
  Clock,
  UserCheck
} from "lucide-react";

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const groupedFeatures = getFeaturesByGroup();
  const location = useLocation();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0B0F19] text-slate-100">
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r border-slate-800 bg-[#0E1322] transition-all duration-300 ${
          sidebarOpen ? "w-64" : "w-16"
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white shadow-lg shadow-indigo-500/30">
              FO
            </div>
            {sidebarOpen && (
              <div>
                <div className="text-sm font-bold tracking-wider text-white">FestOS</div>
                <div className="text-[10px] text-slate-400">EPINOIA 2026</div>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
            title="Toggle Sidebar"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
          {NAV_GROUPS.map((group) => {
            const features = groupedFeatures[group];
            const hasFeatures = features && features.length > 0;

            return (
              <div key={group} className="space-y-1">
                {sidebarOpen ? (
                  <div className="px-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {group}
                  </div>
                ) : (
                  <div className="my-2 h-[1px] bg-slate-800" />
                )}

                {hasFeatures ? (
                  features.map((feature) => {
                    const isActive = location.pathname.startsWith(feature.path);
                    return (
                      <Link
                        key={feature.id}
                        to={feature.path}
                        className={`flex items-center space-x-3 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                          isActive
                            ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                            : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
                        }`}
                      >
                        <Layers size={16} className="shrink-0" />
                        {sidebarOpen && <span className="truncate">{feature.label}</span>}
                      </Link>
                    );
                  })
                ) : (
                  sidebarOpen && (
                    <div className="px-3 py-1 text-[11px] text-slate-600 italic">
                      Coming soon
                    </div>
                  )
                )}
              </div>
            );
          })}
        </div>

        {/* System Footer Status */}
        {sidebarOpen && (
          <div className="border-t border-slate-800 p-3 bg-slate-950/40">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>API Online</span>
              </span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                v0.1-foundation
              </span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-800 bg-[#0E1322]/80 px-6 backdrop-blur">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <span>Aarohan Fest</span>
              <ChevronRight size={14} />
              <span className="text-white font-medium">Command Centre</span>
            </div>
            <span className="flex items-center space-x-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400 border border-emerald-500/20">
              <Activity size={12} className="mr-1" />
              OPERATIONAL
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-xs text-slate-300">
              <Clock size={14} className="text-amber-400" />
              <span>Fest Time: <strong>Live UTC</strong></span>
            </div>

            <div className="flex items-center space-x-2.5 rounded-lg bg-indigo-950/40 border border-indigo-800/40 px-3 py-1.5 text-xs text-indigo-300">
              <UserCheck size={14} className="text-indigo-400" />
              <span>Actor: <strong>FESTIVAL_DIRECTOR</strong></span>
            </div>
          </div>
        </header>

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
