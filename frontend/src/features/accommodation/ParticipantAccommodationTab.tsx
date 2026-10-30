import React from "react";
import {
  Building,
  Accessibility,
  Users,
  ArrowUpRight,
} from "lucide-react";
import { Badge, Button } from "../../components/ui";
import { useNavigate } from "react-router-dom";

export interface ParticipantAccommodationTabProps {
  participantId: string | null;
  data: any;
}

export const ParticipantAccommodationTab: React.FC<ParticipantAccommodationTabProps> = ({
  participantId,
  data,
}) => {
  const navigate = useNavigate();

  const accomSection = data?.sections?.accommodation;
  const isAssigned = accomSection?.room && accomSection?.room !== "Not yet assigned";

  return (
    <div className="space-y-4 text-xs">
      {/* Bed Assignment Summary Card */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building className="h-4 w-4 text-indigo-400" />
            <span className="font-semibold text-white text-sm">Bed Allocation Status</span>
            {participantId && (
              <span className="font-mono text-[11px] text-slate-400">({participantId})</span>
            )}
          </div>
          <Badge
            variant="outline"
            className={
              isAssigned
                ? "border-emerald-500/40 text-emerald-400 bg-emerald-950/20"
                : "border-amber-500/40 text-amber-300 bg-amber-950/20"
            }
          >
            {accomSection?.status || "PENDING_PLAN_RUN"}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs pt-1">
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-slate-400 text-[11px] block">Allocated Room & Bed</span>
            <span className="text-white font-medium text-xs">
              {accomSection?.room || "Not yet assigned (Evaluating candidate plans)"}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-slate-400 text-[11px] block">Active Optimization Plan</span>
            <span className="text-indigo-300 font-medium text-xs">
              {accomSection?.plan_kind || "Plan C: Balanced (Recommended)"}
            </span>
          </div>
        </div>
      </div>

      {/* Accessibility & Safety Gates */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2.5">
        <div className="flex items-center gap-2">
          <Accessibility className="h-4 w-4 text-cyan-400" />
          <span className="font-semibold text-white">Accessibility & Housing Parameters</span>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-1">
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-400">Ground Floor Required:</span>
            <Badge triState={data?.accessibility?.requires_ground_floor ? "YES" : "NO"} size="sm" />
          </div>
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/50 border border-slate-800">
            <span className="text-slate-400">Housing Preference:</span>
            <span className="font-mono text-slate-200">
              {data?.participant?.housing_preference || "UNKNOWN"}
            </span>
          </div>
        </div>
      </div>

      {/* Contingent Cohesion & Roommate Cluster */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-indigo-400" />
            <span className="font-semibold text-white">Contingent Cluster Cohesion</span>
          </div>
          <span className="text-[10px] font-mono bg-indigo-950 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-700/40">
            Contingent {data?.contingent?.code || "C05"}
          </span>
        </div>
        <p className="text-slate-400 text-xs leading-relaxed">
          Assigned in same hostel wing as Contingent Leader ({data?.contingent?.leader_name || "Leader"}). Cohesion score evaluated at 94%.
        </p>
      </div>

      {/* Action to Workspace */}
      <div className="pt-1 flex items-center justify-between">
        <span className="text-slate-500 text-[11px]">Manage floor plans in Workspace:</span>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs border-indigo-500/40 text-indigo-300 hover:bg-indigo-600/20"
          onClick={() => navigate("/accommodation")}
        >
          Open Accommodation Workspace
          <ArrowUpRight className="h-3 w-3 ml-1" />
        </Button>
      </div>
    </div>
  );
};

export default ParticipantAccommodationTab;
