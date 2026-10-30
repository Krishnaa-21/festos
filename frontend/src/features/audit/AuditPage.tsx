import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  Tabs,
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  DataTable,
  Column,
  ConfirmWithReason,
  Modal,
  KpiTile,
  MaskedField,
  useToast,
} from "../../components/ui";
import {
  ShieldCheck,
  FileCheck,
  AlertTriangle,
  Lock,
  Download,
  Clock,
  KeyRound,
  Eye,
  RefreshCw,
  PlusCircle,
} from "lucide-react";

export const AuditPage: React.FC = () => {
  const { user } = useAuth();
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("events");
  const [page, setPage] = useState(1);
  const [filterAction, setFilterAction] = useState("");
  const [filterEntity, setFilterEntity] = useState("");

  // Modals state
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<{ id: string; action: "approve" | "reject" } | null>(null);
  const [inspectEvent, setInspectEvent] = useState<any>(null);

  // 1. Audit Events Query
  const { data: eventsData, isLoading: eventsLoading, refetch: refetchEvents } = useQuery({
    queryKey: ["audit_events", page, filterAction, filterEntity],
    queryFn: async () => {
      const params: any = { page, page_size: 15 };
      if (filterAction) params.action = filterAction;
      if (filterEntity) params.entity_type = filterEntity;
      return api.get<any>("/api/v1/audit/events", { params });
    },
    enabled: activeTab === "events",
  });

  // 2. Overrides Query
  const { data: overridesData, isLoading: overridesLoading, refetch: refetchOverrides } = useQuery({
    queryKey: ["overrides"],
    queryFn: async () => {
      return api.get<any>("/api/v1/overrides", { params: { page: 1, page_size: 50 } });
    },
    enabled: activeTab === "overrides",
  });

  // 3. Approvals Query
  const { data: approvalsData, isLoading: approvalsLoading, refetch: refetchApprovals } = useQuery({
    queryKey: ["approvals"],
    queryFn: async () => {
      return api.get<any>("/api/v1/approvals", { params: { page: 1, page_size: 50 } });
    },
    enabled: activeTab === "approvals",
  });

  // 4. Break-Glass Grants Query
  const { data: breakGlassData, isLoading: bgLoading, refetch: refetchBg } = useQuery({
    queryKey: ["break_glass"],
    queryFn: async () => {
      return api.get<any>("/api/v1/auth/break-glass");
    },
    enabled: activeTab === "break_glass",
  });

  // 5. RBAC Matrix Query
  const { data: permissionsData, isLoading: permsLoading } = useQuery({
    queryKey: ["permissions_matrix"],
    queryFn: async () => {
      return api.get<any>("/api/v1/auth/permissions");
    },
    enabled: activeTab === "matrix",
  });

  // Verify Hash Chain Mutation
  const verifyMutation = useMutation({
    mutationFn: async () => api.get<any>("/api/v1/audit/verify"),
    onSuccess: (res) => {
      setVerifyResult(res);
      setVerifyModalOpen(true);
      if (res.valid) {
        addToast({
          type: "success",
          title: "Cryptographic Chain Verified",
          message: `Verified ${res.verified_count} events from genesis hash with zero discrepancies.`,
        });
      } else {
        addToast({
          type: "error",
          title: "Audit Tampering Detected",
          message: `Broken event: ${res.broken_event_id}`,
        });
      }
    },
  });

  // Create Override Mutation
  const createOverrideMutation = useMutation({
    mutationFn: async ({ reason }: { reason: string }) => {
      return api.post<any>("/api/v1/overrides", {
        entity_type: "room",
        entity_id: "RM_MANUAL_OVR",
        constraint_code: "MANUAL_CAPACITY_BYPASS",
        reason,
        risk_level: "HIGH",
      });
    },
    onSuccess: () => {
      addToast({
        type: "success",
        title: "Override Recorded",
        message: "Constraint relaxation successfully logged in register and immutable audit log.",
      });
      refetchOverrides();
      setOverrideModalOpen(false);
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Override Failed",
        message: err?.message || "Failed to record override",
      });
    },
  });

  // Approval Decision Mutation
  const approvalDecisionMutation = useMutation({
    mutationFn: async ({ id, action, reason }: { id: string; action: "approve" | "reject"; reason: string }) => {
      return api.post<any>(`/api/v1/approvals/${id}/${action}`, { reason });
    },
    onSuccess: (_, variables) => {
      addToast({
        type: "success",
        title: `Change ${variables.action === "approve" ? "Approved & Executed" : "Rejected"}`,
        message: "Decision logged in immutable audit register.",
      });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["pending_approvals_count"] });
      refetchApprovals();
      setSelectedApproval(null);
    },
    onError: (err: any) => {
      addToast({
        type: "error",
        title: "Decision Failed",
        message: err?.message || "Action failed",
      });
    },
  });

  // Break-glass request from inline click
  const handleBreakGlassRequest = async (entity: string, field: string, reason: string) => {
    await api.post<any>("/api/v1/auth/break-glass", {
      entity,
      field,
      reason,
      minutes: 15,
    });
    addToast({
      type: "success",
      title: "Break-Glass Elevation Granted",
      message: `Temporary 15-minute access granted for ${field} on ${entity}`,
    });
    refetchEvents();
    if (activeTab === "break_glass") refetchBg();
  };

  // CSV Export Download
  const handleExportCsv = async () => {
    try {
      const response = await fetch("/api/v1/audit/export/csv", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("festos_token") || ""}`,
        },
      });
      if (!response.ok) throw new Error("Failed to export audit CSV");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `festos_audit_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      addToast({
        type: "info",
        title: "CSV Export Complete",
        message: "Masked audit report downloaded successfully.",
      });
    } catch (err: any) {
      addToast({
        type: "error",
        title: "Export Error",
        message: err.message || "Failed to download audit CSV",
      });
    }
  };

  // Columns for Audit Events
  const eventColumns: Column<any>[] = [
    {
      key: "timestamp",
      header: "Timestamp",
      width: "160px",
      render: (row) => (
        <span className="font-mono text-[11px] text-slate-300">
          {new Date(row.timestamp).toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })}
        </span>
      ),
    },
    {
      key: "action",
      header: "Action / Operation",
      render: (row) => (
        <span className="font-semibold text-indigo-300 font-mono text-xs">{row.action}</span>
      ),
    },
    {
      key: "entity",
      header: "Entity Scope",
      render: (row) => (
        <span className="text-slate-300 font-mono text-[11px]">
          {row.entity_type}:{row.entity_id}
        </span>
      ),
    },
    {
      key: "actor",
      header: "Actor & Role",
      render: (row) => (
        <div className="flex flex-col text-[11px]">
          <span className="font-semibold text-slate-200">{row.actor_name}</span>
          <span className="text-slate-400 text-[10px]">{row.actor_role}</span>
        </div>
      ),
    },
    {
      key: "reason",
      header: "Recorded Rationale",
      render: (row) => (
        <span className="text-slate-400 italic truncate max-w-xs block text-[11px]">
          {row.reason || "System operational baseline"}
        </span>
      ),
    },
    {
      key: "hash",
      header: "Chain Hash",
      width: "120px",
      render: (row) => (
        <span
          className="font-mono text-[10px] text-emerald-400 truncate block max-w-[100px]"
          title={`Prev: ${row.prev_hash}\nCurr: ${row.current_hash}`}
        >
          {row.current_hash ? `${row.current_hash.substring(0, 10)}...` : "GENESIS"}
        </span>
      ),
    },
    {
      key: "inspect",
      header: "",
      width: "60px",
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setInspectEvent(row)}
          title="Inspect state snapshot"
          leftIcon={<Eye className="h-3.5 w-3.5" />}
        />
      ),
    },
  ];

  // Columns for Overrides
  const overrideColumns: Column<any>[] = [
    {
      key: "approved_at",
      header: "Recorded At",
      render: (row) => (
        <span className="font-mono text-[11px] text-slate-300">
          {new Date(row.approved_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: "entity",
      header: "Entity",
      render: (row) => (
        <span className="font-mono text-xs text-indigo-300">{row.entity_type}:{row.entity_id}</span>
      ),
    },
    {
      key: "constraint_code",
      header: "Constraint Relaxed",
      render: (row) => (
        <Badge variant="outline" className="border-amber-500/40 text-amber-300 font-mono text-[10px]">
          {row.constraint_code}
        </Badge>
      ),
    },
    {
      key: "reason",
      header: "Mandatory Reason",
      render: (row) => <span className="text-slate-200 text-xs">{row.reason}</span>,
    },
    {
      key: "risk_level",
      header: "Risk",
      render: (row) => <Badge severity={row.risk_level} />,
    },
    {
      key: "approved_by",
      header: "Authorized By",
      render: (row) => <span className="font-semibold text-slate-300 text-xs">{row.approved_by}</span>,
    },
  ];

  // Columns for Approvals
  const approvalColumns: Column<any>[] = [
    {
      key: "created_at",
      header: "Queued At",
      render: (row) => (
        <span className="font-mono text-[11px] text-slate-300">
          {row.created_at ? new Date(row.created_at).toLocaleString() : "-"}
        </span>
      ),
    },
    {
      key: "entity",
      header: "Target Entity",
      render: (row) => (
        <span className="font-mono text-xs text-indigo-300">{row.entity_type}:{row.entity_id}</span>
      ),
    },
    {
      key: "required_role",
      header: "Required Approver",
      render: (row) => (
        <span className="font-mono text-xs text-slate-200">{row.required_role}</span>
      ),
    },
    {
      key: "reason",
      header: "Proposed Reason",
      render: (row) => <span className="text-slate-300 text-xs">{row.reason || "Standard Change"}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <Badge status={row.status} />,
    },
    {
      key: "actions",
      header: "Sign-off",
      render: (row) =>
        row.status === "PENDING" ? (
          <div className="flex items-center space-x-1.5">
            <Button
              variant="primary"
              size="sm"
              onClick={() => setSelectedApproval({ id: row.id, action: "approve" })}
              className="text-[11px] py-1 px-2.5"
            >
              Approve
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setSelectedApproval({ id: row.id, action: "reject" })}
              className="text-[11px] py-1 px-2.5"
            >
              Reject
            </Button>
          </div>
        ) : (
          <span className="text-[11px] text-slate-500 italic">
            Signed by {row.approved_by || "System"}
          </span>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center space-x-2.5">
            <ShieldCheck className="h-7 w-7 text-indigo-400" />
            <span>Audit & Permissions Command</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Immutable SHA-256 chained audit ledger, operational approvals inbox, and role-based access control.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => verifyMutation.mutate()}
            isLoading={verifyMutation.isPending}
            leftIcon={<FileCheck className="h-4 w-4 text-emerald-400" />}
            data-testid="verify-chain-button"
          >
            Verify Hash Chain
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            leftIcon={<Download className="h-4 w-4" />}
          >
            Export Masked CSV
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setOverrideModalOpen(true)}
            leftIcon={<PlusCircle className="h-4 w-4" />}
          >
            Record Override
          </Button>
        </div>
      </div>

      {/* Top Level KPI Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiTile
          label="Audit Immutability"
          value="ENFORCED"
          icon={<Lock className="h-4 w-4 text-emerald-400" />}
          subtext="Append-only DB triggers active"
        />
        <KpiTile
          label="Pending Approvals"
          value={approvalsData?.items ? approvalsData.items.filter((a: any) => a.status === "PENDING").length : 0}
          icon={<Clock className="h-4 w-4 text-amber-400" />}
          subtext="High-risk operational gates"
          warning={approvalsData?.items && approvalsData.items.some((a: any) => a.status === "PENDING")}
        />
        <KpiTile
          label="Active Overrides"
          value={overridesData?.total ?? 0}
          icon={<AlertTriangle className="h-4 w-4 text-orange-400" />}
          subtext="All recorded with rationale"
        />
        <KpiTile
          label="Active Break-Glass"
          value={breakGlassData?.grants ? breakGlassData.grants.length : 0}
          icon={<KeyRound className="h-4 w-4 text-indigo-400" />}
          subtext="Temporary 15m unmasking TTL"
        />
      </div>

      {/* Main Tab Navigation */}
      <Tabs
        activeTab={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: "events", label: "Audit Timeline", icon: <FileCheck className="h-4 w-4" /> },
          { id: "overrides", label: "Override Register", icon: <AlertTriangle className="h-4 w-4" /> },
          { id: "approvals", label: "Approvals Inbox", icon: <Clock className="h-4 w-4" /> },
          { id: "break_glass", label: "Break-Glass Log", icon: <Lock className="h-4 w-4" /> },
          { id: "matrix", label: "Role-Permission Matrix", icon: <ShieldCheck className="h-4 w-4" /> },
        ]}
      />

      {/* Tab 1: Audit Timeline */}
      {activeTab === "events" && (
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <input
              type="text"
              placeholder="Filter by action (e.g. accommodation.assign_room)..."
              value={filterAction}
              onChange={(e) => {
                setFilterAction(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none w-72"
            />
            <input
              type="text"
              placeholder="Filter by entity type (e.g. room)..."
              value={filterEntity}
              onChange={(e) => {
                setFilterEntity(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none w-56"
            />
            <Button variant="ghost" size="sm" onClick={() => refetchEvents()} leftIcon={<RefreshCw className="h-3.5 w-3.5" />}>
              Refresh
            </Button>
          </div>

          <DataTable
            columns={eventColumns}
            data={eventsData?.items || []}
            total={eventsData?.total || 0}
            page={page}
            pageSize={15}
            onPageChange={setPage}
            isLoading={eventsLoading}
            emptyMessage="No audit records match your filters."
          />
        </div>
      )}

      {/* Tab 2: Override Register */}
      {activeTab === "overrides" && (
        <div className="space-y-4">
          <DataTable
            columns={overrideColumns}
            data={overridesData?.items || []}
            total={overridesData?.total || 0}
            isLoading={overridesLoading}
            emptyMessage="No operational overrides currently recorded."
          />
        </div>
      )}

      {/* Tab 3: Approvals Inbox */}
      {activeTab === "approvals" && (
        <div className="space-y-4">
          <DataTable
            columns={approvalColumns}
            data={approvalsData?.items || []}
            total={approvalsData?.total || 0}
            isLoading={approvalsLoading}
            emptyMessage="No pending operational approvals in queue."
          />
        </div>
      )}

      {/* Tab 4: Break-Glass Log */}
      {activeTab === "break_glass" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Active Temporary Access Grants</CardTitle>
              <CardDescription>
                Emergency field elevations auto-expire after 15 minutes. Masked fields become unmasked only for the granted user.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {bgLoading ? (
                <div className="text-xs text-slate-400 py-4">Loading active grants...</div>
              ) : !breakGlassData?.grants || breakGlassData.grants.length === 0 ? (
                <div className="text-xs text-slate-500 py-6 text-center italic">
                  No active break-glass grants currently open. All sensitive fields are masked.
                </div>
              ) : (
                <div className="divide-y divide-slate-800">
                  {breakGlassData.grants.map((g: any) => (
                    <div key={g.id} className="py-3 flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-bold text-amber-400">{g.entity}</span>
                          <span className="text-xs text-slate-400">→</span>
                          <span className="font-mono text-xs text-white">{g.field}</span>
                          <Badge variant="outline" className="border-emerald-500/30 text-emerald-300 text-[10px]">ACTIVE</Badge>
                        </div>
                        <p className="text-xs text-slate-300 italic">"{g.reason}"</p>
                      </div>
                      <div className="text-right text-xs text-slate-400 font-mono">
                        Expires: {new Date(g.expires_at).toLocaleTimeString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Interactive Masked Field Elevation Test Bench */}
          <Card className="border-slate-800 bg-[#0E1526]">
            <CardHeader>
              <CardTitle className="text-sm">Field Masking & Inline Break-Glass Access</CardTitle>
              <CardDescription>
                Sensitive fields remain masked by default according to role policies. Click any masked field to request emergency break-glass unmasking.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Participant Phone (PII)
                  </div>
                  <div className="flex items-center space-x-3">
                    <MaskedField
                      value="+91-XXXXX-9988"
                      isMasked={true}
                      entity="participant:2041"
                      field="phone"
                      onBreakGlass={handleBreakGlassRequest}
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Medical & Allergy Note (Protected)
                  </div>
                  <div className="flex items-center space-x-3">
                    <MaskedField
                      value="[RESTRICTED MEDICAL DATA]"
                      isMasked={true}
                      entity="participant:2041"
                      field="medical_details"
                      onBreakGlass={handleBreakGlassRequest}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 5: Role-Permission Matrix */}
      {activeTab === "matrix" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">FestOS Nine-Role RBAC Capability Matrix</CardTitle>
              <CardDescription>
                Granular module and action permissions governing operational access across departments.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {permsLoading ? (
                <div className="text-xs text-slate-400 py-4">Loading RBAC matrix...</div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(permissionsData?.roles || {}).map(([role, perms]: [string, any]) => {
                    const isCurrentUserRole = user?.role === role;
                    return (
                      <div
                        key={role}
                        className={`rounded-xl border p-4 transition-all ${
                          isCurrentUserRole
                            ? "border-indigo-500/60 bg-indigo-950/20 shadow-md shadow-indigo-500/10"
                            : "border-slate-800 bg-slate-900/40"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2.5">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-xs font-bold text-white">{role}</span>
                            {isCurrentUserRole && (
                              <span className="rounded bg-indigo-600/30 px-2 py-0.5 text-[10px] font-bold text-indigo-300 border border-indigo-500/40">
                                YOUR CURRENT ROLE
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-slate-400">
                            {perms.length} granted permission{perms.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {perms.map((p: string) => (
                            <span
                              key={p}
                              className="rounded-md border border-slate-700 bg-slate-950 px-2 py-0.5 font-mono text-[11px] text-slate-300"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Verification Result Modal */}
      <Modal
        isOpen={verifyModalOpen}
        onClose={() => setVerifyModalOpen(false)}
        title={
          <div className="flex items-center space-x-2 text-white">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            <span>Cryptographic Hash-Chain Verification</span>
          </div>
        }
        size="md"
      >
        {verifyResult && (
          <div className="space-y-4 text-xs">
            <div
              className={`rounded-lg p-3 border ${
                verifyResult.valid
                  ? "border-emerald-500/40 bg-emerald-950/20 text-emerald-200"
                  : "border-red-500/40 bg-red-950/20 text-red-200"
              }`}
            >
              <div className="font-bold text-sm">
                {verifyResult.valid ? "Hash Chain Integral & Tamper-Free" : "Hash Divergence Detected!"}
              </div>
              <p className="mt-1 text-slate-300">
                Verified {verifyResult.verified_count} sequential operations chained from genesis hash.
              </p>
            </div>

            <div className="space-y-1.5 rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-[11px]">
              <div>
                <span className="text-slate-500">Genesis Hash: </span>
                <span className="text-slate-300">{verifyResult.genesis_hash?.substring(0, 24)}...</span>
              </div>
              <div>
                <span className="text-slate-500">Latest Hash: </span>
                <span className="text-emerald-400">{verifyResult.latest_hash?.substring(0, 24)}...</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setVerifyModalOpen(false)}>
                Dismiss
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Record Override Confirmation Modal (mandatory reason) */}
      <ConfirmWithReason
        isOpen={overrideModalOpen}
        onClose={() => setOverrideModalOpen(false)}
        title="Record Operational Override"
        description="Relaxing a constraint requires recording an explicit operational reason under FestOS principles."
        confirmText="Commit Override"
        placeholder="Reason for relaxation (e.g. VIP contingent emergency overflow accommodation approved by Director)..."
        isLoading={createOverrideMutation.isPending}
        onConfirm={(reason) => createOverrideMutation.mutateAsync({ reason })}
      />

      {/* Approval / Rejection Decision Modal (mandatory reason) */}
      {selectedApproval && (
        <ConfirmWithReason
          isOpen={true}
          onClose={() => setSelectedApproval(null)}
          title={`${selectedApproval.action === "approve" ? "Authorize & Execute" : "Reject"} High-Risk Change`}
          description="Every approval gate decision requires a recorded rationale entered into the immutable audit log."
          confirmText={selectedApproval.action === "approve" ? "Sign-off & Execute" : "Reject Change"}
          placeholder="Enter sign-off explanation or rejection rationale..."
          isLoading={approvalDecisionMutation.isPending}
          riskLevel={selectedApproval.action === "approve" ? "HIGH" : "LOW"}
          onConfirm={(reason) =>
            approvalDecisionMutation.mutateAsync({
              id: selectedApproval.id,
              action: selectedApproval.action,
              reason,
            })
          }
        />
      )}

      {/* Inspect State Snapshot Modal */}
      <Modal
        isOpen={!!inspectEvent}
        onClose={() => setInspectEvent(null)}
        title={`Inspect Event: ${inspectEvent?.action}`}
        description={`Audit ID: ${inspectEvent?.id} | ${inspectEvent?.timestamp}`}
        size="lg"
      >
        {inspectEvent && (
          <div className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <div className="font-bold text-amber-300 mb-1">Before State</div>
                <pre className="text-[10px] text-slate-300 overflow-x-auto max-h-48">
                  {JSON.stringify(inspectEvent.before_state, null, 2)}
                </pre>
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <div className="font-bold text-emerald-300 mb-1">After State</div>
                <pre className="text-[10px] text-slate-300 overflow-x-auto max-h-48">
                  {JSON.stringify(inspectEvent.after_state, null, 2)}
                </pre>
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <span className="text-slate-500">Recorded Reason: </span>
              <span className="text-slate-200">{inspectEvent.reason || "None recorded"}</span>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setInspectEvent(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
