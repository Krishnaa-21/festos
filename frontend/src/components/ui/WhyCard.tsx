import React from "react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./Card";
import { Badge } from "./Badge";
import { HelpCircle, AlertTriangle, Users, IndianRupee } from "lucide-react";

export interface DecisionCardData {
  id: string;
  subject: string;
  recommendation: string;
  hard_satisfied: boolean;
  soft_relaxed?: Array<{ constraint: string; reason: string }>;
  alternatives_rejected?: Array<{ option: string; why: string }>;
  cost_impact?: number | null;
  people_affected?: number;
  approved_by?: string | null;
  created_at: string;
}

export interface WhyCardProps {
  decision: DecisionCardData;
  className?: string;
}

export const WhyCard: React.FC<WhyCardProps> = ({ decision, className }) => {
  return (
    <Card className={className} glow={!decision.hard_satisfied}>
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <HelpCircle className="h-4 w-4 text-indigo-400" />
            <CardTitle className="text-sm font-bold text-white">{decision.subject}</CardTitle>
          </div>
          <p className="text-xs text-indigo-300/90 font-medium">{decision.recommendation}</p>
        </div>
        <Badge triState={decision.hard_satisfied ? "YES" : "NO"}>
          {decision.hard_satisfied ? "Hard Constraints Met" : "Hard Constraint Relaxed"}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-4 pt-4 text-xs">
        {/* Soft Constraints Relaxed */}
        {decision.soft_relaxed && decision.soft_relaxed.length > 0 && (
          <div className="space-y-1.5 rounded-lg bg-amber-950/20 border border-amber-500/20 p-3">
            <div className="flex items-center space-x-1.5 font-semibold text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Soft Constraints Relaxed (in ladder order)</span>
            </div>
            <ul className="space-y-1 pl-4 list-disc text-slate-300">
              {decision.soft_relaxed.map((sr, idx) => (
                <li key={idx}>
                  <strong className="text-amber-200">{sr.constraint}:</strong> {sr.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Alternatives Rejected */}
        {decision.alternatives_rejected && decision.alternatives_rejected.length > 0 && (
          <div className="space-y-1.5 rounded-lg bg-slate-900/60 border border-slate-800 p-3">
            <div className="font-semibold text-slate-300">Alternatives Evaluated & Rejected</div>
            <ul className="space-y-1 pl-4 list-disc text-slate-400">
              {decision.alternatives_rejected.map((alt, idx) => (
                <li key={idx}>
                  <span className="text-slate-200">{alt.option}</span> — {alt.why}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Operational Metrics Impact */}
        <div className="flex items-center space-x-6 text-slate-300">
          <div className="flex items-center space-x-1.5">
            <Users className="h-3.5 w-3.5 text-slate-500" />
            <span>People Affected: <strong>{decision.people_affected ?? 0}</strong></span>
          </div>
          {decision.cost_impact !== undefined && decision.cost_impact !== null && (
            <div className="flex items-center space-x-1">
              <IndianRupee className="h-3.5 w-3.5 text-slate-500" />
              <span>Cost Impact: <strong>₹{decision.cost_impact.toLocaleString("en-IN")}</strong></span>
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between text-[11px] text-slate-400">
        <span>Approved by: <strong className="text-slate-200">{decision.approved_by || "Pending"}</strong></span>
        <span>{new Date(decision.created_at).toLocaleString()}</span>
      </CardFooter>
    </Card>
  );
};
