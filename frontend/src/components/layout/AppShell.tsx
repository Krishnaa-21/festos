import React, { useState, useEffect } from "react";
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
  HelpCircle,
  Command,
  AlertTriangle,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { OfflineStatusPill } from "./OfflineStatusPill";
import { CommandCenterModal } from "../../features/commands/CommandCenterModal";
import { KeyboardShortcutsModal } from "./KeyboardShortcutsModal";
import { VolunteerMobileView } from "../../features/checkin/VolunteerMobileView";

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [isCommandCenterOpen, setIsCommandCenterOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);

  const { user, logout, hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const isVolunteer = user?.role === "VOLUNTEER";

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

  // Keyboard shortcuts: Cmd+K / Ctrl+K, '/', '?', Chords 'g' then 'o'/'c'/'m'/'r'
  useEffect(() => {
    let lastKey = "";
    let keyTimeout: any;

    const handleKeyDown = (e: KeyboardEvent) => {
      // 1. Global Command Center Shortcut (Cmd+K or Ctrl+K)
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandCenterOpen(true);
        return;
      }

      // Don't intercept single-key navigation chords if typing inside an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
        return;
      }

      // Shortcut: '?' (Shift + /) toggles keyboard help overlay
      if (e.key === "?") {
        e.preventDefault();
        setIsShortcutsOpen((prev) => !prev);
        return;
      }

      // Shortcut: '/' opens global command bar
      if (e.key === "/") {
        e.preventDefault();
        setIsCommandCenterOpen(true);
        return;
      }

      // Navigation Chords: 'g' then <key>
      if (e.key.toLowerCase() === "g") {
        lastKey = "g";
        clearTimeout(keyTimeout);
        keyTimeout = setTimeout(() => {
          lastKey = "";
        }, 1000);
      } else if (lastKey === "g") {
        const nextKey = e.key.toLowerCase();
        lastKey = "";
        if (nextKey === "o") {
          e.preventDefault();
          navigate("/dashboard");
        } else if (nextKey === "c") {
          e.preventDefault();
          navigate("/checkin");
        } else if (nextKey === "m") {
          e.preventDefault();
          navigate("/merchandise");
        } else if (nextKey === "r") {
          e.preventDefault();
          navigate("/reports");
        }
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
      if (isVolunteer) {
        // Volunteer terminals are strictly role-gated to Check-In and Merchandise
        return feat.id === "checkin" || feat.id === "merchandise";
      }
      if (!feat.permissions || feat.permissions.length === 0) return true;
      return feat.permissions.some((p) => hasPermission(p));
    });
  }

  // Check if current route is role-gated for volunteer
  const isVolunteerAllowedRoute =
    location.pathname === "/checkin" ||
    location.pathname.startsWith("/checkin/") ||
    location.pathname === "/merchandise" ||
    location.pathname.startsWith("/merchandise/") ||
    location.pathname === "/dashboard" ||
    location.pathname === "/" ||
    location.pathname === "/volunteer";

  return (
    <div
      className={`flex h-screen w-screen overflow-hidden ${
        theme === "light" ? "bg-slate-50 text-slate-900" : "bg-[#070B14] text-slate-100"
      }`}
    >
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

        {/* Navigation Groups - Filtered by role permissions */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
          {NAV_GROUPS.map((group) => {
            const features = filteredGrouped[group] || [];
            const hasFeatures = features.length > 0;

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
                <span className="text-[11px] font-mono">PWA Enabled</span>
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

          {/* AI Command Center Global Button / Search Bar */}
          <button
            type="button"
            data-testid="global-command-bar"
            onClick={() => setIsCommandCenterOpen(true)}
            className="hidden md:flex items-center justify-between w-80 rounded-xl border border-slate-700 bg-slate-950/70 py-1.5 px-3 text-xs text-slate-400 hover:border-indigo-500/60 transition-all shadow-inner"
          >
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-slate-500" />
              <span className="truncate">Type command or search...</span>
            </div>
            <kbd className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700 flex items-center gap-0.5">
              <Command className="w-2.5 h-2.5" /> K
            </kbd>
          </button>

          {/* Right Action Elements */}
          <div className="flex items-center space-x-3">
            {/* PWA Offline / Online Status Pill with Pending Queue Badge */}
            <OfflineStatusPill />

            {/* Demo Clock */}
            <div
              className="hidden lg:flex items-center space-x-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300 font-mono shadow-sm"
              title="Current Fest Operational Clock (UTC / IST)"
            >
              <Clock size={14} className="text-amber-400 shrink-0" />
              <span>{new Date().toLocaleTimeString([], { hour12: false })} IST</span>
            </div>

            {/* Keyboard Shortcuts Help Overlay Button */}
            <button
              data-testid="help-shortcuts-btn"
              onClick={() => setIsShortcutsOpen(true)}
              className="rounded-lg border border-slate-800 bg-slate-900/60 p-2 text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
              title="Keyboard Shortcuts Help (?)"
            >
              <HelpCircle size={16} />
            </button>

            {/* Approvals Bell with Badge (Hidden for volunteers) */}
            {!isVolunteer && (
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
            )}

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
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        setIsCommandCenterOpen(true);
                      }}
                      className="w-full flex items-center space-x-2 px-3 py-2 text-slate-300 hover:bg-slate-800 rounded-lg text-left"
                    >
                      <Command size={14} />
                      <span>AI Command Center</span>
                    </button>
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        setIsShortcutsOpen(true);
                      }}
                      className="w-full flex items-center space-x-2 px-3 py-2 text-slate-300 hover:bg-slate-800 rounded-lg text-left"
                    >
                      <HelpCircle size={14} />
                      <span>Keyboard Shortcuts (?)</span>
                    </button>
                  </div>

                  <div className="pt-1 border-t border-slate-800">
                    <button
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center space-x-2 px-3 py-2 text-red-400 hover:bg-red-950/30 rounded-lg text-left"
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

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {/* Volunteer Role Check & Landing */}
          {isVolunteer ? (
            location.pathname === "/dashboard" || location.pathname === "/" || location.pathname === "/volunteer" ? (
              <VolunteerMobileView />
            ) : isVolunteerAllowedRoute ? (
              <Outlet />
            ) : (
              /* Role-gated barrier for volunteer trying to access restricted director screens */
              <div
                data-testid="volunteer-restricted-view"
                className="max-w-md mx-auto p-6 rounded-2xl border border-rose-500/40 bg-rose-950/20 text-center space-y-4 my-8"
              >
                <AlertTriangle className="w-10 h-10 mx-auto text-rose-400" />
                <div className="space-y-1">
                  <h2 className="text-base font-bold text-white">
                    Access Restricted: Volunteer Terminal
                  </h2>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Under FestOS security principles, Volunteer accounts only have operational access to Check-In Desks and Merchandise Counters with minimal personal data exposure.
                  </p>
                </div>
                <Button
                  variant="primary"
                  onClick={() => navigate("/dashboard")}
                  className="bg-indigo-600 hover:bg-indigo-500 font-bold"
                >
                  Return to Volunteer Counter
                </Button>
              </div>
            )
          ) : (
            <Outlet />
          )}
        </main>
      </div>

      {/* Global Modals */}
      <CommandCenterModal
        isOpen={isCommandCenterOpen}
        onClose={() => setIsCommandCenterOpen(false)}
      />
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
    </div>
  );
};
