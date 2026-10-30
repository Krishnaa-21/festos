import React from "react";
import { cn } from "../../lib/utils";
import { TrendingUp, TrendingDown, AlertCircle } from "lucide-react";

export interface KpiTileProps {
  label: string;
  value: string | number;
  subtext?: React.ReactNode;
  icon?: React.ReactNode;
  trend?: {
    direction: "up" | "down" | "neutral";
    value: string;
  };
  warning?: boolean;
  className?: string;
}

export const KpiTile: React.FC<KpiTileProps> = ({
  label,
  value,
  subtext,
  icon,
  trend,
  warning = false,
  className,
}) => {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-800 bg-[#0E1526]/90 p-5 shadow-sm backdrop-blur transition-all",
        warning && "border-amber-500/40 bg-amber-950/10",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
        {icon && <span className="text-slate-400">{icon}</span>}
      </div>

      <div className="mt-2 flex items-baseline justify-between">
        <span className="text-2xl font-extrabold text-white font-mono">{value}</span>
        {trend && (
          <span
            className={cn(
              "inline-flex items-center space-x-0.5 text-xs font-semibold",
              trend.direction === "up" ? "text-emerald-400" : "text-rose-400"
            )}
          >
            {trend.direction === "up" ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            <span>{trend.value}</span>
          </span>
        )}
      </div>

      {subtext && (
        <div className="mt-1 flex items-center text-xs text-slate-400">
          {warning && <AlertCircle className="h-3 w-3 text-amber-400 mr-1 shrink-0" />}
          <span>{subtext}</span>
        </div>
      )}
    </div>
  );
};
