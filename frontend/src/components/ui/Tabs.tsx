import React from "react";
import { cn } from "../../lib/utils";

export interface TabItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className }) => {
  return (
    <div className={cn("flex space-x-1 border-b border-slate-800 bg-slate-900/40 p-1 rounded-lg", className)}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              "flex items-center space-x-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all select-none",
              isActive
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/20"
                : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
            )}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge && <span className="ml-1.5">{tab.badge}</span>}
          </button>
        );
      })}
    </div>
  );
};
