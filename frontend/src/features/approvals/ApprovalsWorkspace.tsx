import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface ApprovalItem {
  id: string;
  change_set_id: string | null;
  entity_type: string;
  entity_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  required_role: string;
  requested_by: string;
  reason: string;
  risk_kind: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  payload_preview: unknown;
}

const RISK_COLORS: Record<string, string> = {
  SAFETY: "bg-red-500/20 text-red-400 border-red-500/30",
  PRIVACY: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  HIGH: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  LOW: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  MEDIUM: "bg-sky-500/20 text-sky-400 border-sky-500/30",
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  PENDING: <Clock className="h-4 w-4 text-amber-400" />,
  APPROVED: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  REJECTED: <XCircle className="h-4 w-4 text-red-400" />,
};

const ApprovalsWorkspace: React.FC = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [statusFilter, setStatusFilter] = useState("PENDING");
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [decisionReason, setDecisionReason] = useState("");
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [expandedPayload, setExpandedPayload] = useState<string | null>(null);

  const { data, isLoading } = useQuery<{ items: ApprovalItem[]; total: number }>({
    queryKey: ["approvals", statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = { page_size: "50" };
      if (statusFilter !== "ALL") params.status = statusFilter;
      const res = await api.get<{ items: ApprovalItem[]; total: number }>("/api/v1/approvals", { params });
      return res;
    },
    refetchInterval: 8000,
  });

  const { data: policies } = useQuery({
    queryKey: ["approval_policies"],
    queryFn: () => api.get<{ policies: unknown[] }>("/api/v1/approvals/policies"),
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/v1/approvals/${id}/approve`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      addToast({ title: "Approved", message: "Change approved and executed.", type: "success" });
      setIsDetailOpen(false);
      setDecisionReason("");
    },
    onError: (e: Error) => addToast({ title: "Error", message: e.message, type: "error" }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/v1/approvals/${id}/reject`, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      addToast({ title: "Rejected", message: "Change rejected and logged.", type: "warning" });
      setIsDetailOpen(false);
      setDecisionReason("");
    },
    onError: (e: Error) => addToast({ title: "Error", message: e.message, type: "error" }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const openDetail = (item: ApprovalItem) => {
    setSelectedApproval(item);
    setDecisionReason("");
    setIsDetailOpen(true);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-amber-400" />
            Approvals Queue
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Pending operational changes requiring Director sign-off — {total} total
          </p>
        </div>
        <div className="flex gap-2">
          {["ALL", "PENDING", "APPROVED", "REJECTED"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === s
                  ? "bg-violet-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Policies Banner */}
      {(policies as any)?.policies && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
            <FileText className="h-4 w-4" /> Approval Policies
          </h3>
          <div className="flex flex-wrap gap-2">
            {((policies as any)?.policies ?? []).map((p: any) => (
              <span key={p.risk_kind} className={`px-2 py-1 rounded text-xs border ${RISK_COLORS[p.risk_kind] ?? "bg-slate-700 text-slate-300"}`}>
                {p.risk_kind} → {p.required_roles.join(", ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Items List */}
      {isLoading ? (
        <div className="text-center py-16 text-slate-500">Loading approvals…</div>
      ) : items.length === 0 ? (
        <div className="text-center py-20">
          <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto mb-3 opacity-60" />
          <p className="text-slate-400 font-medium">No {statusFilter !== "ALL" ? statusFilter.toLowerCase() : ""} approvals</p>
          <p className="text-slate-600 text-sm mt-1">Pending items appear here when changes require Director sign-off.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-slate-800/80 border border-slate-700/50 rounded-xl p-4 cursor-pointer hover:border-violet-500/50 transition-all group"
              onClick={() => openDetail(item)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{STATUS_ICONS[item.status] ?? STATUS_ICONS.PENDING}</div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white">{item.entity_type}</span>
                      <code className="text-xs text-slate-400 bg-slate-900/60 px-1.5 py-0.5 rounded">{item.entity_id}</code>
                      <span className={`px-2 py-0.5 text-xs border rounded ${RISK_COLORS[item.risk_kind] ?? "bg-slate-700 text-slate-400 border-slate-600"}`}>
                        {item.risk_kind}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-1">{item.reason}</p>
                    <p className="text-xs text-slate-600 mt-0.5">
                      Requested by <span className="text-slate-500">{item.requested_by}</span>
                      {" · "}{item.required_role}{" · "}
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                <Badge status={item.status}>
                  {item.status}
                </Badge>
              </div>

              {/* Expandable payload preview */}
              {Boolean(item.payload_preview) && (
                <div
                  className="mt-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedPayload(expandedPayload === item.id ? null : item.id);
                  }}
                >
                  <button className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">
                    {expandedPayload === item.id ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    Payload preview
                  </button>
                  {expandedPayload === item.id && (
                    <pre className="mt-1 text-xs text-slate-400 bg-slate-900/60 rounded p-2 overflow-auto max-h-32">
                      {JSON.stringify(item.payload_preview, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Decision Modal */}
      {selectedApproval && (
        <Modal isOpen={isDetailOpen} onClose={() => setIsDetailOpen(false)} title="Review Approval Request">
          <div className="space-y-4">
            <div className="bg-slate-900/60 rounded-lg p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Entity</span>
                <span className="text-white font-mono">{selectedApproval.entity_type} / {selectedApproval.entity_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Risk</span>
                <span className={`px-2 py-0.5 rounded text-xs border ${RISK_COLORS[selectedApproval.risk_kind] ?? "text-slate-300"}`}>
                  {selectedApproval.risk_kind}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Requested by</span>
                <span className="text-white">{selectedApproval.requested_by}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Required role</span>
                <span className="text-white">{selectedApproval.required_role}</span>
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Operational Reason for Change</label>
              <p className="text-sm text-slate-300 bg-slate-900/40 rounded p-3">{selectedApproval.reason}</p>
            </div>

            {selectedApproval.status === "PENDING" && (
              <>
                <div>
                  <label className="text-xs text-slate-400 uppercase tracking-wider block mb-1.5">
                    Your Decision Justification <span className="text-red-400">*</span>
                  </label>
                  <textarea
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white resize-none focus:outline-none focus:border-violet-500"
                    rows={3}
                    placeholder="Mandatory rationale for your decision…"
                    value={decisionReason}
                    onChange={(e) => setDecisionReason(e.target.value)}
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <Button
                    variant="primary"
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    disabled={!decisionReason.trim() || approveMutation.isPending}
                    onClick={() => approveMutation.mutate({ id: selectedApproval.id, reason: decisionReason })}
                  >
                    <CheckCircle2 className="h-4 w-4 mr-2" /> Approve & Execute
                  </Button>
                  <Button
                    variant="danger"
                    className="flex-1"
                    disabled={!decisionReason.trim() || rejectMutation.isPending}
                    onClick={() => rejectMutation.mutate({ id: selectedApproval.id, reason: decisionReason })}
                  >
                    <XCircle className="h-4 w-4 mr-2" /> Reject
                  </Button>
                </div>
              </>
            )}

            {selectedApproval.status !== "PENDING" && (
              <div className="bg-slate-900/60 rounded-lg p-3 text-sm">
                <span className="text-slate-400">Decision by</span>{" "}
                <span className="text-white">{selectedApproval.approved_by}</span>
                {selectedApproval.rejection_reason && (
                  <p className="text-red-400 mt-1">{selectedApproval.rejection_reason}</p>
                )}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ApprovalsWorkspace;
