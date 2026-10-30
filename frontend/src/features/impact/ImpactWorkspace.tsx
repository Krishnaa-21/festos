import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../../api/client";
import { ImpactReportData, ImpactTreeNode } from "./types";
import { SeverityPill } from "../../components/ui/SeverityPill";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Drawer } from "../../components/ui/Drawer";
import {
  GitFork,
  ChevronRight,
  ChevronDown,
  Users,
  Building,
  Calendar,
  MapPin,
  Utensils,
  Truck,
  UserCheck,
  Package,
  Layers,
  Search,
} from "lucide-react";

export const ImpactWorkspace: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const incidentIdParam = searchParams.get("incident_id") || searchParams.get("change_id") || "INC-2026-001";

  const [selectedIncidentId, setSelectedIncidentId] = useState(incidentIdParam);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    grp_participants: true,
    grp_accom: true,
    grp_events: true,
    grp_transport: true,
    grp_food: true,
  });
  const [inspectedEntity, setInspectedEntity] = useState<ImpactTreeNode | null>(null);

  // Sync state if query param changes
  useEffect(() => {
    if (incidentIdParam && incidentIdParam !== selectedIncidentId) {
      setSelectedIncidentId(incidentIdParam);
    }
  }, [incidentIdParam, selectedIncidentId]);

  const { data: reportData } = useQuery<ImpactReportData>({
    queryKey: ["impact_tree", selectedIncidentId],
    queryFn: async () => {
      const res = await api.get<ImpactReportData>("/api/v1/impact/tree", {
        params: { incident_id: selectedIncidentId },
      });
      return res;
    },
  });

  const toggleNode = (nodeId: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  };

  const expandAll = () => {
    const next: Record<string, boolean> = {};
    const traverse = (nodes: ImpactTreeNode[]) => {
      for (const n of nodes) {
        next[n.id] = true;
        if (n.children) traverse(n.children);
      }
    };
    if (reportData?.tree) traverse(reportData.tree);
    setExpandedNodes(next);
  };

  const collapseAll = () => {
    setExpandedNodes({});
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "participant":
        return <Users className="h-4 w-4 text-sky-400" />;
      case "accommodation":
        return <Building className="h-4 w-4 text-emerald-400" />;
      case "event":
        return <Calendar className="h-4 w-4 text-amber-400" />;
      case "venue":
        return <MapPin className="h-4 w-4 text-purple-400" />;
      case "vendor":
        return <Utensils className="h-4 w-4 text-rose-400" />;
      case "transport":
        return <Truck className="h-4 w-4 text-indigo-400" />;
      case "staff":
        return <UserCheck className="h-4 w-4 text-teal-400" />;
      default:
        return <Package className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6" data-testid="impact-workspace">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600/20 text-indigo-400">
              <GitFork className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">Impact Analysis & Blast Radius</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Traverse interconnected festival dependencies across Participants, Accommodation, Events, Venues, Vendors, Transport, and Staff.
          </p>
        </div>

        {/* Change Set / Incident Selector */}
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-lg p-1.5">
          <Search className="h-3.5 w-3.5 text-slate-500 ml-1.5" />
          <span className="text-[11px] text-slate-400">Blast Radius for:</span>
          <select
            value={selectedIncidentId}
            onChange={(e) => {
              setSelectedIncidentId(e.target.value);
              setSearchParams({ incident_id: e.target.value });
            }}
            data-testid="blast-radius-select"
            className="rounded bg-slate-950 px-2 py-1 text-xs text-white border border-slate-700 focus:outline-none focus:border-indigo-500"
          >
            <option value="INC-2026-001">INC-2026-001 (Hostel 3 Closure)</option>
            <option value="INC-2026-002">INC-2026-002 (Vendor VND04 Shutdown)</option>
            <option value="CS-0103">CS-0103 (Late Contingent C05 Shift)</option>
            <option value="CS-0104">CS-0104 (Amphitheatre Rain Relocation)</option>
          </select>
        </div>
      </div>

      {/* Root Disruption Banner */}
      {reportData && (
        <div className="rounded-xl border border-indigo-500/40 bg-[#0E1526] p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Badge status="REJECTED">ROOT DISRUPTION EVENT</Badge>
              <span className="font-mono text-xs font-bold text-slate-300">{reportData.rootChange.id}</span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-indigo-400 font-semibold">{reportData.rootChange.action}</span>
            </div>
            <p className="text-xs text-slate-200 font-medium">{reportData.rootChange.description}</p>
          </div>

          <div className="flex items-center space-x-3 text-xs text-slate-400 shrink-0">
            <span>By: {reportData.rootChange.actor}</span>
            <span>•</span>
            <span>{new Date(reportData.rootChange.triggeredAt).toLocaleTimeString()}</span>
          </div>
        </div>
      )}

      {/* Affected Entity Counts by Type (KPI Chips) */}
      {reportData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5" data-testid="counts-by-type">
          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Users className="h-4 w-4 text-sky-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.participants}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Participants</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Building className="h-4 w-4 text-emerald-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.accommodation}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Rooms</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Calendar className="h-4 w-4 text-amber-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.events}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Events</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <MapPin className="h-4 w-4 text-purple-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.venues}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Venues</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Utensils className="h-4 w-4 text-rose-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.vendors}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Vendors</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Truck className="h-4 w-4 text-indigo-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.transport}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Shuttles</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <UserCheck className="h-4 w-4 text-teal-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.staff}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Staff</div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0A0F1D] p-3 text-center">
            <Package className="h-4 w-4 text-slate-400 mx-auto" />
            <div className="mt-1 text-lg font-bold font-mono text-white">
              {reportData.countsByType.inventory}
            </div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Inventory</div>
          </div>
        </div>
      )}

      {/* Main Grid: Interactive Impact Tree + Before vs After Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Interactive Visual Impact Tree */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Interactive Visual Impact Tree
              </h2>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm" className="text-xs h-7" onClick={expandAll} data-testid="expand-all-btn">
                Expand All
              </Button>
              <Button variant="ghost" size="sm" className="text-xs h-7" onClick={collapseAll} data-testid="collapse-all-btn">
                Collapse All
              </Button>
            </div>
          </div>

          {/* Tree Node Renderer */}
          <div className="space-y-2" data-testid="impact-tree-container">
            {reportData?.tree.map((node) => {
              const isExpanded = !!expandedNodes[node.id];
              return (
                <div key={node.id} className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
                  {/* Category Root Node */}
                  <div
                    onClick={() => toggleNode(node.id)}
                    className="flex items-center justify-between cursor-pointer hover:bg-slate-800/40 rounded p-1.5 transition-colors"
                    data-testid={`tree-node-${node.id}`}
                  >
                    <div className="flex items-center space-x-2.5">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                      )}
                      {getNodeIcon(node.type)}
                      <span className="text-xs font-bold text-white">{node.label}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-mono font-bold text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">
                        {node.peopleAffected} Pax
                      </span>
                      <SeverityPill severity={node.severity} />
                    </div>
                  </div>

                  {/* Children Nodes (Indented) */}
                  {isExpanded && node.children && node.children.length > 0 && (
                    <div className="mt-2 pl-6 space-y-1.5 border-l-2 border-slate-800 ml-3">
                      {node.children.map((child) => (
                        <div
                          key={child.id}
                          onClick={() => setInspectedEntity(child)}
                          data-testid={`tree-leaf-${child.id}`}
                          className="flex items-center justify-between rounded-md p-2 bg-slate-950/60 border border-slate-800/60 hover:border-indigo-500/50 cursor-pointer transition-colors"
                        >
                          <div className="flex items-center space-x-2">
                            {getNodeIcon(child.type)}
                            <span className="text-xs font-medium text-slate-200">{child.label}</span>
                          </div>

                          <div className="flex items-center space-x-2">
                            <Badge
                              status={
                                child.status === "MITIGATED" || child.status === "REALLOCATED"
                                  ? "SUCCESS"
                                  : "PENDING"
                              }
                              className="text-[9px]"
                            >
                              {child.status}
                            </Badge>
                            <SeverityPill severity={child.severity} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 1 Col: Before-versus-After Comparison */}
        <div className="rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
              Before vs After Recovery Diff
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Comparison of festival operational state pre-disruption vs post-mitigation.
            </p>
          </div>

          <div className="space-y-3" data-testid="before-after-comparison">
            {reportData?.beforeAfterComparison.map((item, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-slate-800 bg-slate-900/50 p-3.5 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">{item.metric}</span>
                  <span
                    className={`font-mono text-xs font-bold ${
                      item.status === "improved"
                        ? "text-emerald-400"
                        : item.status === "degraded"
                        ? "text-amber-400"
                        : "text-slate-400"
                    }`}
                  >
                    {item.delta}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/60">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Before Disruption:</span>
                    <span className="text-slate-300 font-mono">{item.before}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">After Mitigation:</span>
                    <span className="text-emerald-400 font-mono font-semibold">{item.after}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-2">
            <Link to="/incidents">
              <Button variant="secondary" size="sm" className="w-full text-xs">
                Back to Disruption Console
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Side Inspection Drawer for Clicked Entity */}
      <Drawer
        isOpen={!!inspectedEntity}
        onClose={() => setInspectedEntity(null)}
        title={inspectedEntity?.label || "Entity Inspection"}
        width="max-w-md"
      >
        {inspectedEntity && (
          <div className="space-y-4 text-xs text-slate-200">
            <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Entity ID:</span>
                <span className="font-mono font-bold text-white">{inspectedEntity.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Type:</span>
                <span className="font-bold uppercase text-indigo-400">{inspectedEntity.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Current Status:</span>
                <Badge status="SUCCESS">{inspectedEntity.status}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Blast Severity:</span>
                <SeverityPill severity={inspectedEntity.severity} />
              </div>
            </div>

            {inspectedEntity.details && (
              <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-2">
                <h4 className="text-[11px] font-bold uppercase text-slate-400">Operational Allocation</h4>
                {Object.entries(inspectedEntity.details).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-slate-400 capitalize">{key.replace(/([A-Z])/g, " $1")}:</span>
                    <span className="font-semibold text-white">{String(val)}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2">
              <Button
                variant="primary"
                size="sm"
                className="w-full text-xs"
                onClick={() => setInspectedEntity(null)}
              >
                Close Inspector
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default ImpactWorkspace;
