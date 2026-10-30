import React, { useState, useEffect, useRef } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { NAV_GROUPS, getFeaturesByGroup, FeatureDefinition, NavGroup } from "../../app/registry";
import { useAuth } from "../../features/auth/AuthContext";
import {
  ChevronRight,
  Activity,
  Menu,
  X,
  Layers,
  Clock,
  Bell,
  Search,
  LogOut,
  Sun,
  Moon,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  const { user, logout, hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Pending approvals count for bell icon
  const { data: pendingApprovals } = useQuery({
    queryKey: ["pending_approvals_count"],
    queryFn: async () => {
      try {
        const res = await api.get<any>("/api/v1/approvals", {
          params: { status: "PENDING", page: 1, page_size: 1 },
        });
        return res?.total ?? 0;
      } catch {
        return 0;
      }
    },
    refetchInterval: 15000,
  });

  // Theme toggle
  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    if (next === "light") {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
    }
  };

  // Keyboard shortcuts: '/' for search, 'g' then 'o' for overview
  useEffect(() => {
    let lastKey = "";
    let keyTimeout: NodeJS.Timeout;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept if typing inside an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }

      // Shortcut: '/' focuses global search / command bar
      if (e.key === "/") {
        e.preventDefault();
        setTimeout(() => searchInputRef.current?.focus(), 50);
        return;
      }

      // Shortcut: 'g' then 'o' navigates to overview (/dashboard)
      if (e.key.toLowerCase() === "g") {
        lastKey = "g";
        clearTimeout(keyTimeout);
        keyTimeout = setTimeout(() => {
          lastKey = "";
        }, 1000);
      } else if (lastKey === "g" && e.key.toLowerCase() === "o") {
        e.preventDefault();
        lastKey = "";
        navigate("/dashboard");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      clearTimeout(keyTimeout);
    };
  }, [navigate]);

  // Filter features by role permissions
  const allGrouped = getFeaturesByGroup();
  const filteredGrouped = {} as Record<NavGroup, FeatureDefinition[]>;

  for (const group of NAV_GROUPS) {
    const list = allGrouped[group] || [];
    filteredGrouped[group] = list.filter((feat) => {
      if (!feat.permissions || feat.permissions.length === 0) return true;
      return feat.permissions.some((p) => hasPermission(p));
    });
  }

  return (
    <div className={`flex h-screen w-screen overflow-hidden ${theme === "light" ? "bg-slate-50 text-slate-900" : "bg-[#070B14] text-slate-100"}`}>
      {/* Sidebar */}
      <aside
        className={`flex flex-col border-r transition-all duration-300 ${
          theme === "light"
            ? "border-slate-200 bg-white shadow-sm"
            : "border-slate-800 bg-[#0A0F1D]"
        } ${sidebarOpen ? "w-64" : "w-16"}`}
      >
        {/* Brand Header */}
        <div
          className={`flex h-16 items-center justify-between border-b px-4 ${
            theme === "light" ? "border-slate-200" : "border-slate-800"
          }`}
        >
          <div className="flex items-center space-x-3 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-600 font-bold text-white shadow-md shadow-indigo-500/25">
              FO
            </div>
            {sidebarOpen && (
              <div>
                <div className="text-sm font-extrabold tracking-wider text-white">FestOS</div>
                <div className="text-[10px] text-slate-400">EPINOIA 2026</div>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            title="Toggle Sidebar"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Navigation Groups - Filtered by permissions per Section 18 */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
          {NAV_GROUPS.map((group) => {
            const features = filteredGrouped[group] || [];
            const hasFeatures = features.length > 0;

            // If a group has no permitted features, hide it for that role
            if (!hasFeatures && sidebarOpen && user?.role !== "FESTIVAL_DIRECTOR") {
              return null;
            }

            return (
              <div key={group} className="space-y-1">
                {sidebarOpen ? (
                  <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
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
                        className={`flex items-center space-x-2.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-all ${
                          isActive
                            ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30"
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

        {/* Sidebar Footer with Active Role */}
        {sidebarOpen && (
          <div className="border-t border-slate-800 p-3 bg-slate-950/60">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[11px] font-mono">Live Sync</span>
              </span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
                {user?.role || "GUEST"}
              </span>
            </div>
          </div>
        )}
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar */}
        <header
          className={`flex h-16 items-center justify-between border-b px-6 backdrop-blur ${
            theme === "light"
              ? "border-slate-200 bg-white/80"
              : "border-slate-800 bg-[#0A0F1D]/80"
          }`}
        >
          {/* Breadcrumb & Status */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <span>Aarohan Fest</span>
              <ChevronRight size={14} />
              <span className="text-white font-semibold">Command Centre</span>
            </div>
            <span className="flex items-center space-x-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-bold text-emerald-400 border border-emerald-500/20">
              <Activity size={12} className="mr-1" />
              OPERATIONAL
            </span>
          </div>

          {/* Search / Command Bar Slot */}
          <div className="relative hidden md:flex items-center w-80">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search or press '/' for command..."
              data-testid="global-command-bar"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 py-1.5 pl-8 pr-12 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <kbd className="absolute right-2.5 top-2 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700">
              /
            </kbd>
          </div>

          {/* Right Action Elements */}
          <div className="flex items-center space-x-3.5">
            {/* Demo Clock */}
            <div
              className="flex items-center space-x-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300 font-mono shadow-sm"
              title="Current Fest Operational Clock (UTC / IST)"
            >
              <Clock size={14} className="text-amber-400 shrink-0" />
              <span>{new Date().toLocaleTimeString([], { hour12: false })} IST</span>
            </div>

            {/* Approvals Bell with Badge */}
            <Link
              to="/audit"
              className="relative rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
              title="Approvals Inbox"
            >
              <Bell size={16} />
              {(pendingApprovals ?? 0) > 0 && (
                <span
                  className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] font-bold text-white shadow-sm"
                  data-testid="approvals-badge"
                >
                  {pendingApprovals}
                </span>
              )}
            </Link>

            {/* Light/Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              className="rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
              title="Toggle Theme"
            >
              {theme === "dark" ? <Sun size={16} className="text-amber-400" /> : <Moon size={16} />}
            </button>

            {/* User Profile & Menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center space-x-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-800 transition-colors"
              >
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-indigo-600/30 text-indigo-300 font-bold text-[11px] border border-indigo-500/30">
                  {user?.full_name?.substring(0, 2).toUpperCase() || "FD"}
                </div>
                <div className="text-left hidden sm:block">
                  <div className="text-xs font-bold leading-tight">{user?.full_name || "User"}</div>
                  <div className="text-[10px] text-slate-400 leading-tight">{user?.role || "VOLUNTEER"}</div>
                </div>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-800 bg-[#0E1526] p-2 text-xs shadow-2xl z-50">
                  <div className="px-3 py-2 border-b border-slate-800">
                    <div className="font-bold text-white truncate">{user?.full_name}</div>
                    <div className="text-[11px] text-slate-400 truncate">{user?.email}</div>
                    <div className="mt-1">
                      <Badge variant="outline" className="border-indigo-500/40 text-indigo-300 text-[10px]">
                        {user?.role}
                      </Badge>
                    </div>
                  </div>

                  <div className="py-1">
                    <Link
                      to="/audit"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center space-x-2 rounded-lg px-3 py-1.5 text-slate-300 hover:bg-slate-800 hover:text-white"
                    >
                      <ShieldCheck size={14} className="text-indigo-400" />
                      <span>Security & Audit</span>
                    </Link>
                  </div>

                  <div className="pt-1 border-t border-slate-800">
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                        navigate("/login");
                      }}
                      className="flex w-full items-center space-x-2 rounded-lg px-3 py-1.5 text-rose-400 hover:bg-rose-950/30"
                    >
                      <LogOut size={14} />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
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
