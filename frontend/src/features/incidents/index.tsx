import { FeatureDefinition } from "../../app/registry";
import { IncidentCenterWorkspace } from "./IncidentCenterWorkspace";
import { AlertTriangle } from "lucide-react";

export const incidentsFeature: FeatureDefinition = {
  id: "incidents",
  label: "Incident Command Center",
  group: "Incident Center",
  path: "/incidents",
  icon: AlertTriangle,
  permissions: ["incidents:read"],
  routes: [
    {
      path: "",
      element: <IncidentCenterWorkspace />,
    },
  ],
};

export default incidentsFeature;
