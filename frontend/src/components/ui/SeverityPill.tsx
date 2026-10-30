import React from "react";
import { AlertOctagon, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { cn } from "../../lib/utils";

export type SeverityType = 1 | 2 | 3 | 4 | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface SeverityPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  severity: SeverityType;
  showIcon?: boolean;
}

export const SeverityPill: React.FC<SeverityPillProps> = ({
  severity,
  showIcon = true,
  className,
  ...props
}) => {
  const norm =
    typeof severity === "string"
      ? { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 }[severity.toUpperCase()] || 1
      : severity;

  const config = {
    4: {
      label: "CRITICAL",
      color: "bg-red-500/20 text-red-300 border-red-500/40 shadow-red-500/10",
      icon: <AlertOctagon className="h-3 w-3 text-red-400 shrink-0" />,
    },
    3: {
      label: "HIGH",
      color: "bg-orange-500/20 text-orange-300 border-orange-500/40 shadow-orange-500/10",
      icon: <AlertTriangle className="h-3 w-3 text-orange-400 shrink-0" />,
    },
    2: {
      label: "MEDIUM",
      color: "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-amber-500/10",
      icon: <AlertCircle className="h-3 w-3 text-amber-400 shrink-0" />,
    },
    1: {
      label: "LOW",
      color: "bg-blue-500/20 text-blue-300 border-blue-500/40 shadow-blue-500/10",
      icon: <Info className="h-3 w-3 text-blue-400 shrink-0" />,
    },
  }[norm as 1 | 2 | 3 | 4];

  return (
    <span
      className={cn(
        "inline-flex items-center space-x-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold tracking-wider shadow-sm select-none",
        config.color,
        className
      )}
      {...props}
    >
      {showIcon && config.icon}
      <span>{config.label}</span>
    </span>
  );
};
