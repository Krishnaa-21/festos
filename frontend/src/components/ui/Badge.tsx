import React from "react";
import { cn } from "../../lib/utils";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertOctagon,
  AlertTriangle,
  AlertCircle,
  Info,
  Clock,
  Ban,
} from "lucide-react";

export type TriState = "YES" | "NO" | "UNKNOWN";
export type SeverityLevel = 1 | 2 | 3 | 4 | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type StatusType =
  | "SUCCESS"
  | "APPLIED"
  | "PENDING"
  | "PENDING_APPROVAL"
  | "REJECTED"
  | "ACTIVE"
  | "REVOKED"
  | "EXPIRED"
  | "ARCHIVED";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  triState?: TriState;
  severity?: SeverityLevel;
  status?: StatusType | string;
  variant?: "default" | "outline" | "solid";
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  triState,
  severity,
  status,
  variant = "default",
  size = "md",
  className,
  children,
  ...props
}) => {
  const sizeClasses = size === "sm" ? "text-[10px] px-1.5 py-0.5 gap-1" : "text-xs px-2.5 py-1 gap-1.5";

  // 1. Tri-State Rendering
  if (triState) {
    const config = {
      YES: {
        bg: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
        icon: <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" data-testid="icon-yes" />,
        label: "YES",
      },
      NO: {
        bg: "bg-rose-500/15 text-rose-300 border-rose-500/30",
        icon: <XCircle className="h-3 w-3 text-rose-400 shrink-0" data-testid="icon-no" />,
        label: "NO",
      },
      UNKNOWN: {
        bg: "bg-amber-500/15 text-amber-300 border-amber-500/30",
        icon: <HelpCircle className="h-3 w-3 text-amber-400 shrink-0" data-testid="icon-unknown" />,
        label: "UNKNOWN",
      },
    }[triState];

    return (
      <span
        className={cn(
          "inline-flex items-center font-semibold rounded-md border",
          sizeClasses,
          config.bg,
          className
        )}
        data-testid={`badge-tri-${triState.toLowerCase()}`}
        {...props}
      >
        {config.icon}
        <span>{children || config.label}</span>
      </span>
    );
  }

  // 2. Severity Rendering (Never colour-only: always shows distinct icon & text)
  if (severity !== undefined) {
    const normSev =
      typeof severity === "string"
        ? { LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4 }[severity.toUpperCase()] || 1
        : severity;

    const sevConfig = {
      4: {
        bg: "bg-red-500/20 text-red-300 border-red-500/40",
        icon: <AlertOctagon className="h-3.5 w-3.5 text-red-400 shrink-0" data-testid="icon-sev-critical" />,
        label: "CRITICAL",
      },
      3: {
        bg: "bg-orange-500/20 text-orange-300 border-orange-500/40",
        icon: <AlertTriangle className="h-3.5 w-3.5 text-orange-400 shrink-0" data-testid="icon-sev-high" />,
        label: "HIGH",
      },
      2: {
        bg: "bg-amber-500/20 text-amber-300 border-amber-500/40",
        icon: <AlertCircle className="h-3.5 w-3.5 text-amber-400 shrink-0" data-testid="icon-sev-medium" />,
        label: "MEDIUM",
      },
      1: {
        bg: "bg-blue-500/20 text-blue-300 border-blue-500/40",
        icon: <Info className="h-3.5 w-3.5 text-blue-400 shrink-0" data-testid="icon-sev-low" />,
        label: "LOW",
      },
    }[normSev as 1 | 2 | 3 | 4] || {
      bg: "bg-slate-500/20 text-slate-300 border-slate-500/40",
      icon: <Info className="h-3.5 w-3.5 text-slate-400 shrink-0" />,
      label: "INFO",
    };

    return (
      <span
        className={cn(
          "inline-flex items-center font-bold tracking-wider rounded-md border",
          sizeClasses,
          sevConfig.bg,
          className
        )}
        data-testid={`badge-severity-${sevConfig.label.toLowerCase()}`}
        {...props}
      >
        {sevConfig.icon}
        <span>{children || sevConfig.label}</span>
      </span>
    );
  }

  // 3. Operational Status Rendering
  if (status) {
    const s = status.toUpperCase();
    let statusClass = "bg-slate-800 text-slate-300 border-slate-700";
    let icon = <Info className="h-3 w-3 shrink-0" />;

    if (s === "SUCCESS" || s === "APPLIED" || s === "ACTIVE") {
      statusClass = "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
      icon = <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />;
    } else if (s === "PENDING" || s === "PENDING_APPROVAL") {
      statusClass = "bg-amber-500/15 text-amber-300 border-amber-500/30 animate-pulse-subtle";
      icon = <Clock className="h-3 w-3 text-amber-400 shrink-0" />;
    } else if (s === "REJECTED" || s === "REVOKED") {
      statusClass = "bg-rose-500/15 text-rose-300 border-rose-500/30";
      icon = <Ban className="h-3 w-3 text-rose-400 shrink-0" />;
    }

    return (
      <span
        className={cn(
          "inline-flex items-center font-medium rounded-md border",
          sizeClasses,
          statusClass,
          className
        )}
        data-testid={`badge-status-${s.toLowerCase()}`}
        {...props}
      >
        {icon}
        <span>{children || status.replace(/_/g, " ")}</span>
      </span>
    );
  }

  // Fallback Generic Badge
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-md border border-slate-700 bg-slate-800/60 text-slate-300",
        sizeClasses,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
