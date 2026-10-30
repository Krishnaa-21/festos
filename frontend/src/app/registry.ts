import React from "react";

export const NAV_GROUPS = [
  "Overview",
  "Participants",
  "Contingents",
  "Check-in",
  "Accommodation",
  "Events & Venues",
  "Logistics",
  "Merchandise",
  "Vendors & Food",
  "Staff & Shifts",
  "Transportation",
  "Incident Center",
  "Impact Analysis",
  "Scenario Simulator",
  "Fest Pre-Mortem",
  "Unknowns Burn-down",
  "AI Command Center",
  "Data Reconciliation",
  "Reports",
  "Audit & Permissions",
] as const;

export type NavGroup = typeof NAV_GROUPS[number];

export interface FeatureRoute {
  path: string;
  element: React.ReactNode;
  index?: boolean;
}

export interface FeatureDefinition {
  id: string;
  label: string;
  group: NavGroup;
  path: string;
  icon?: any;
  permissions?: string[];
  routes?: FeatureRoute[];
}

// Auto-register features through import.meta.glob
const featureModules = import.meta.glob<Record<string, any>>(
  "../features/*/index.{ts,tsx}",
  { eager: true }
);

export function getRegisteredFeatures(): FeatureDefinition[] {
  const features: FeatureDefinition[] = [];

  for (const path in featureModules) {
    const mod = featureModules[path];
    const feature = mod.default || mod.feature || mod;

    if (feature && feature.id && feature.label && feature.group) {
      features.push({
        id: feature.id,
        label: feature.label,
        group: feature.group,
        path: feature.path || `/${feature.id}`,
        icon: feature.icon,
        permissions: feature.permissions || [],
        routes: feature.routes || [],
      });
    }
  }

  return features;
}

export function getFeaturesByGroup(): Record<NavGroup, FeatureDefinition[]> {
  const features = getRegisteredFeatures();
  const grouped = {} as Record<NavGroup, FeatureDefinition[]>;

  for (const g of NAV_GROUPS) {
    grouped[g] = [];
  }

  for (const f of features) {
    if (grouped[f.group]) {
      grouped[f.group].push(f);
    }
  }

  return grouped;
}
