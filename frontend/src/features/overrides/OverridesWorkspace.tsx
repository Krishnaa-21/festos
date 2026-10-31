import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import { ShieldAlert, Plus, AlertOctagon } from "lucide-react";

interface OverrideItem {
  id: string;
  entity_type: string;
  entity_id: string;
  constraint_code: string;
  reason: string;
  approved_by: string;
  approved_at: string | null;
  risk_level: "LOW" | "HIGH" | "CRITICAL";
  status: string;
}

const RISK_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-500/20 text-red-400 border-red-500/30",
  HIGH: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  LOW: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

const OverridesWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [riskFilter, setRiskFilter] = useState("ALL");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [form, setForm] = useState({
    entity_type: "",
    entity_id: "",
    constraint_code: "",
    reason: "",
    risk_level: "HIGH",
  });

  const { data, isLoading } = useQuery<{ items: OverrideItem[]; total: number }>({
    queryKey: ["overrides", riskFilter],
    queryFn: async () => {
      const params: Record<string, string> = { page_size: "50" };
      if (riskFilter !== "ALL") params.risk_level = riskFilter;
      const res = await api.get<{ items: OverrideItem[]; total: number }>("/api/v1/overrides", { params });
      return res;
    },
    refetchInterval: 15000,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post("/api/v1/overrides", form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["overrides"] });
      addToast({ title: "Override Recorded", message: "Constraint exception logged in register.", type: "warning" });
      setIsCreateOpen(false);
      setForm({ entity_type: "", entity_id: "", constraint_code: "", reason: "", risk_level: "HIGH" });
    },
    onError: (e: Error) => addToast({ title: "Error", message: e.message, type: "error" }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-orange-400" />
            Override Register
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Hard constraint exceptions with mandatory recorded justifications — {total} total
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2">
            {["ALL", "CRITICAL", "HIGH", "LOW"].map((r) => (
              <button
                key={r}
                onClick={() => setRiskFilter(r)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  riskFilter === r ? "bg-violet-600 text-white" : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
              >
                {r}
              </button>
            ))}
          </div>
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" /> Record Override
          </Button>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3">
        <AlertOctagon className="h-5 w-5 text-amber-400 mt-0.5 shrink-0" />
        <div className="text-sm">
          <span className="font-semibold text-amber-300">FestOS Override Policy:</span>{" "}
          <span className="text-slate-300">
            Hard constraints (safety, privacy, accessibility, minor protection) are NEVER auto-relaxed.
            Every override requires a mandatory recorded operational rationale and Director sign-off.
          </span>
        </div>
      </div>

      {/* Items */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-500">Loading override register…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-20">
          <ShieldAlert className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 font-medium">No overrides recorded</p>
          <p className="text-slate-600 text-sm mt-1">
            Constraint exceptions appear here when hard rules are bypassed with justification.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="bg-slate-800/80 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white">{item.entity_type}</span>
                    <code className="text-xs text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded">{item.entity_id}</code>
                    <code className="text-xs text-slate-500 bg-slate-900/40 px-1.5 py-0.5 rounded">{item.constraint_code}</code>
                    <span className={`px-2 py-0.5 text-xs border rounded ${RISK_STYLES[item.risk_level] ?? RISK_STYLES.HIGH}`}>
                      {item.risk_level}
                    </span>
                  </div>
                  <p className="text-sm text-slate-300 mt-1.5 line-clamp-2">{item.reason}</p>
                  <p className="text-xs text-slate-600 mt-1">
                    Approved by <span className="text-slate-500">{item.approved_by}</span>
                    {item.approved_at && ` · ${new Date(item.approved_at).toLocaleString()}`}
                  </p>
                </div>
                <Badge severity={item.risk_level}>
                  {item.risk_level}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Record Constraint Override">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Entity Type</label>
              <input
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                placeholder="e.g. room, event, schedule"
                value={form.entity_type}
                onChange={(e) => setForm({ ...form, entity_type: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Entity ID</label>
              <input
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                placeholder="e.g. ROOM-001"
                value={form.entity_id}
                onChange={(e) => setForm({ ...form, entity_id: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Constraint Code</label>
            <input
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
              placeholder="e.g. MAX_CAPACITY, GENDER_SEPARATION"
              value={form.constraint_code}
              onChange={(e) => setForm({ ...form, constraint_code: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Risk Level</label>
            <select
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
              value={form.risk_level}
              onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
            >
              <option value="LOW">LOW</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">
              Mandatory Rationale <span className="text-red-400">*</span>
            </label>
            <textarea
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white resize-none focus:outline-none focus:border-violet-500"
              rows={4}
              placeholder="Why is this constraint being bypassed? What operational necessity justifies this exception?"
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="ghost" className="flex-1" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              className="flex-1 bg-orange-600 hover:bg-orange-700"
              disabled={!form.entity_type || !form.entity_id || !form.constraint_code || !form.reason.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              <ShieldAlert className="h-4 w-4 mr-1.5" /> Record Override
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default OverridesWorkspace;
