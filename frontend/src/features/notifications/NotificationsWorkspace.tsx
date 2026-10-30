import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { NotificationDraft, NotificationAudience, DeliveryLogEntry } from "./types";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useToast } from "../../components/ui/Toast";
import {
  Bell,
  Send,
  CheckCircle2,
  Edit3,
  Users,
  Utensils,
  Building,
  Calendar,
  History,
  CheckCheck,
} from "lucide-react";

export const NotificationsWorkspace: React.FC = () => {
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<"inbox" | "delivery_log">("inbox");
  const [audienceFilter, setAudienceFilter] = useState<string>("ALL");
  const [editingDraft, setEditingDraft] = useState<NotificationDraft | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [sendingDraftId, setSendingDraftId] = useState<string | null>(null);

  // 1. Fetch Drafts
  const { data: draftsData, refetch: refetchDrafts } = useQuery<{ items: NotificationDraft[]; total: number }>({
    queryKey: ["notification_drafts"],
    queryFn: async () => {
      const res = await api.get<{ items: NotificationDraft[]; total: number }>("/api/v1/notifications/drafts");
      return res;
    },
  });

  // 2. Fetch Delivery Log
  const { data: logData, refetch: refetchLog } = useQuery<{ items: DeliveryLogEntry[]; total: number }>({
    queryKey: ["notifications_delivery_log"],
    queryFn: async () => {
      const res = await api.get<{ items: DeliveryLogEntry[]; total: number }>("/api/v1/notifications/log");
      return res;
    },
  });

  // Edit Draft Mutation
  const editMutation = useMutation({
    mutationFn: async ({ id, subject, body }: { id: string; subject: string; body: string }) => {
      return api.post(`/api/v1/notifications/drafts/${id}/edit`, { subject, body });
    },
    onSuccess: () => {
      refetchDrafts();
      addToast({
        title: "Draft Updated",
        message: "Notification broadcast text updated.",
        type: "success",
      });
      setEditingDraft(null);
    },
  });

  // Approve Draft Mutation
  const approveMutation = useMutation({
    mutationFn: async (id: string) => {
      return api.post(`/api/v1/notifications/drafts/${id}/approve`);
    },
    onSuccess: () => {
      refetchDrafts();
      addToast({
        title: "Broadcast Approved",
        message: "Notification authorized for mock dispatch.",
        type: "success",
      });
    },
  });

  // Mock-Send Mutation
  const mockSendMutation = useMutation({
    mutationFn: async (id: string) => {
      setSendingDraftId(id);
      return api.post(`/api/v1/notifications/drafts/${id}/send`);
    },
    onSuccess: (data: any) => {
      setSendingDraftId(null);
      refetchDrafts();
      refetchLog();
      addToast({
        title: "Mock-Send Dispatched",
        message: data?.data?.message || "Broadcast successfully transmitted to recipient group.",
        type: "success",
      });
    },
    onError: () => {
      setSendingDraftId(null);
    },
  });

  const drafts = draftsData?.items || [];
  const logs = logData?.items || [];

  const filteredDrafts = drafts.filter((d) => {
    if (audienceFilter !== "ALL" && d.audience !== audienceFilter) return false;
    return true;
  });

  const getAudienceIcon = (aud: NotificationAudience) => {
    switch (aud) {
      case "LEADERS":
        return <Users className="h-4 w-4 text-sky-400" />;
      case "VOLUNTEERS":
        return <Users className="h-4 w-4 text-teal-400" />;
      case "VENDORS":
        return <Utensils className="h-4 w-4 text-amber-400" />;
      case "COORDINATORS":
        return <Building className="h-4 w-4 text-emerald-400" />;
      case "ORGANISERS":
        return <Calendar className="h-4 w-4 text-purple-400" />;
    }
  };

  return (
    <div className="space-y-6" data-testid="notifications-workspace">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400">
              <Bell className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Broadcast Notifications & Drafts</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Audience-targeted notification inbox: review automated disruption notices, authorize broadcasts, and mock-send.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
          <button
            onClick={() => setActiveTab("inbox")}
            className={`rounded-md px-3 py-1.5 font-semibold transition-all ${
              activeTab === "inbox" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
            }`}
            data-testid="tab-drafts-inbox"
          >
            Drafts Inbox ({drafts.length})
          </button>
          <button
            onClick={() => setActiveTab("delivery_log")}
            className={`rounded-md px-3 py-1.5 font-semibold transition-all flex items-center space-x-1.5 ${
              activeTab === "delivery_log" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
            }`}
            data-testid="tab-delivery-log"
          >
            <History className="h-3.5 w-3.5" />
            <span>Delivery Log ({logs.length})</span>
          </button>
        </div>
      </div>

      {activeTab === "inbox" && (
        <div className="space-y-4">
          {/* Audience Filter Pills */}
          <div className="flex flex-wrap items-center gap-2" data-testid="audience-filter-bar">
            {[
              { id: "ALL", label: "All Audiences" },
              { id: "LEADERS", label: "Contingent Leaders (38)" },
              { id: "VOLUNTEERS", label: "Volunteers (48)" },
              { id: "VENDORS", label: "Food Vendors (14)" },
              { id: "COORDINATORS", label: "Accommodation (12)" },
              { id: "ORGANISERS", label: "Event Organisers (31)" },
            ].map((aud) => (
              <button
                key={aud.id}
                onClick={() => setAudienceFilter(aud.id)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  audienceFilter === aud.id
                    ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/25"
                    : "bg-[#0E1526] text-slate-400 border border-slate-800 hover:border-slate-700 hover:text-slate-200"
                }`}
                data-testid={`filter-${aud.id.toLowerCase()}`}
              >
                {aud.label}
              </button>
            ))}
          </div>

          {/* Drafts List */}
          <div className="space-y-3" data-testid="drafts-list">
            {filteredDrafts.length === 0 ? (
              <div className="rounded-xl border border-slate-800 bg-[#0E1526] p-8 text-center text-xs text-slate-500">
                No notification drafts matching audience filter.
              </div>
            ) : (
              filteredDrafts.map((draft) => (
                <div
                  key={draft.id}
                  className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-3 transition-all hover:border-slate-700"
                  data-testid={`draft-card-${draft.id}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                    <div className="flex items-center space-x-2.5">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 border border-slate-800">
                        {getAudienceIcon(draft.audience)}
                      </div>
                      <div>
                        <span className="font-bold text-white text-xs">{draft.audienceLabel}</span>
                        <span className="text-[11px] text-slate-400 ml-2">({draft.recipientCount} Recipients)</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Badge status={draft.priority === "URGENT" ? "REJECTED" : "PENDING"}>
                        {draft.priority}
                      </Badge>
                      <Badge
                        status={
                          draft.status === "SENT"
                            ? "SUCCESS"
                            : draft.status === "APPROVED"
                            ? "APPLIED"
                            : "PENDING"
                        }
                      >
                        {draft.status}
                      </Badge>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <h3 className="text-sm font-bold text-white">{draft.subject}</h3>
                    <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 rounded-lg p-3 border border-slate-800/60 font-sans">
                      {draft.body}
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 text-xs text-slate-400">
                    <div className="flex items-center space-x-2">
                      {draft.triggerIncidentId && (
                        <span className="text-[11px] text-indigo-400 font-mono">
                          Trigger: {draft.triggerIncidentId} ({draft.triggerEventLabel})
                        </span>
                      )}
                      {draft.approvedBy && (
                        <span className="text-[11px] text-emerald-400">
                          • Authorized by {draft.approvedBy}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      {draft.status !== "SENT" && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-xs h-7"
                            onClick={() => {
                              setEditingDraft(draft);
                              setEditSubject(draft.subject);
                              setEditBody(draft.body);
                            }}
                            data-testid={`edit-draft-btn-${draft.id}`}
                          >
                            <Edit3 className="mr-1.5 h-3 w-3" /> Edit
                          </Button>

                          {draft.status === "DRAFT" && (
                            <Button
                              variant="secondary"
                              size="sm"
                              className="text-xs h-7"
                              onClick={() => approveMutation.mutate(draft.id)}
                              data-testid={`approve-draft-btn-${draft.id}`}
                            >
                              <CheckCircle2 className="mr-1.5 h-3 w-3 text-emerald-400" /> Approve
                            </Button>
                          )}

                          <Button
                            variant="primary"
                            size="sm"
                            className="text-xs h-7"
                            isLoading={sendingDraftId === draft.id}
                            onClick={() => mockSendMutation.mutate(draft.id)}
                            data-testid={`mock-send-btn-${draft.id}`}
                          >
                            <Send className="mr-1.5 h-3 w-3" /> Mock-Send
                          </Button>
                        </>
                      )}

                      {draft.status === "SENT" && (
                        <span className="text-emerald-400 flex items-center text-xs font-semibold">
                          <CheckCheck className="mr-1.5 h-4 w-4" /> Dispatched
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* DELIVERY LOG VIEW */}
      {activeTab === "delivery_log" && (
        <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4" data-testid="delivery-log-view">
          <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Dispatched Transmission Ledger
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Audit trail of outgoing simulated broadcast SMS, WhatsApp, and in-app communications.
              </p>
            </div>
            <Badge status="ACTIVE">{logs.length} Logged</Badge>
          </div>

          <div className="space-y-3">
            {logs.map((log) => (
              <div
                key={log.id}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-2 text-xs"
                data-testid={`log-entry-${log.id}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-slate-400 font-bold">{log.id}</span>
                    <span className="text-slate-500">•</span>
                    <span className="font-semibold text-white">{log.audienceLabel}</span>
                    <span className="text-slate-400">({log.recipientCount} pax)</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
                      {log.channel}
                    </span>
                    <Badge status="SUCCESS">{log.status}</Badge>
                  </div>
                </div>

                <div className="font-bold text-white">{log.subject}</div>
                <p className="text-slate-300 text-[11px] bg-slate-950/60 p-2 rounded">{log.bodyPreview}</p>

                <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400 font-mono">
                  <span>Sent at: {new Date(log.sentAt).toLocaleTimeString()}</span>
                  <span className="text-emerald-400">
                    Delivered: {log.deliveredCount} | Ack: {log.acknowledgedCount}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Notification Draft Modal */}
      <Modal
        isOpen={!!editingDraft}
        onClose={() => setEditingDraft(null)}
        title="Edit Broadcast Draft"
        description="Fine-tune broadcast message wording prior to audience dispatch."
        size="md"
      >
        {editingDraft && (
          <div className="space-y-4 text-xs text-slate-200">
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Subject Line</label>
              <input
                type="text"
                value={editSubject}
                onChange={(e) => setEditSubject(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white"
                data-testid="edit-subject-input"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-slate-300">Message Body</label>
              <textarea
                rows={5}
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 p-2 text-xs text-white focus:outline-none"
                data-testid="edit-body-input"
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800">
              <Button variant="ghost" size="sm" onClick={() => setEditingDraft(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!editSubject.trim() || !editBody.trim()}
                onClick={() =>
                  editMutation.mutate({
                    id: editingDraft.id,
                    subject: editSubject.trim(),
                    body: editBody.trim(),
                  })
                }
                data-testid="save-draft-btn"
              >
                Save Changes
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default NotificationsWorkspace;
