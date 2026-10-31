import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../auth/AuthContext";
import { Shield, Key, User, CheckCircle2 } from "lucide-react";

const ROLE_COLORS: Record<string, string> = {
  FESTIVAL_DIRECTOR: "text-violet-400",
  ACCOMMODATION_LEAD: "text-sky-400",
  EVENT_LEAD: "text-emerald-400",
  LOGISTICS_MANAGER: "text-amber-400",
  MERCHANDISE_MANAGER: "text-pink-400",
  FOOD_OPS_MANAGER: "text-orange-400",
  FINANCE_MANAGER: "text-teal-400",
  VOLUNTEER: "text-slate-400",
  AUDITOR: "text-indigo-400",
};

const UserSessionsWorkspace: React.FC = () => {
  const { user } = useAuth();

  const { data: meData } = useQuery({
    queryKey: ["auth_me"],
    queryFn: () => api.get<any>("/api/v1/auth/me"),
  });

  const { data: permissionsData } = useQuery({
    queryKey: ["auth_permissions"],
    queryFn: () => api.get<{ roles: Record<string, string[]> }>("/api/v1/auth/permissions"),
  });

  const roles = (permissionsData as any)?.roles ?? {};
  const me = meData as any;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Shield className="h-6 w-6 text-violet-400" />
          User Accounts & Sessions
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Active session, RBAC role definitions, and operational permission scopes
        </p>
      </div>

      {/* Current Session Card */}
      <div className="bg-slate-800/80 border border-violet-500/30 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-full bg-violet-600/30 border border-violet-500/40 flex items-center justify-center">
            <User className="h-6 w-6 text-violet-400" />
          </div>
          <div>
            <p className="font-semibold text-white text-lg">{user?.full_name ?? me?.name ?? "—"}</p>
            <p className="text-sm text-slate-400">{user?.email ?? me?.email ?? "—"}</p>
          </div>
          <div className="ml-auto">
            <span className={`text-sm font-semibold ${ROLE_COLORS[user?.role ?? ""] ?? "text-slate-300"}`}>
              {user?.role?.replace(/_/g, " ")}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Active JWT session — full permissions for your role
        </div>
      </div>

      {/* Role-Permission Matrix */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <Key className="h-4 w-4" /> RBAC Permission Matrix
        </h2>
        <div className="space-y-3">
          {Object.entries(roles).map(([role, perms]) => (
            <div key={role} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className={`font-semibold text-sm ${ROLE_COLORS[role] ?? "text-slate-300"}`}>
                  {role.replace(/_/g, " ")}
                </span>
                <span className="text-xs text-slate-500">{(perms as string[]).length} permission{(perms as string[]).length !== 1 ? "s" : ""}</span>
              </div>
              {(perms as string[]).includes("*:*") ? (
                <div className="text-xs bg-violet-500/20 text-violet-300 border border-violet-500/30 rounded px-2 py-1 inline-block">
                  ✦ Superuser — all permissions
                </div>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {(perms as string[]).map((perm) => (
                    <code key={perm} className="text-xs bg-slate-900/60 text-slate-400 px-1.5 py-0.5 rounded">
                      {perm}
                    </code>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UserSessionsWorkspace;
