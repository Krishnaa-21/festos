import type { FeatureDefinition } from "../../app/registry";
import { IncidentCenterWorkspace } from "./IncidentCenterWorkspace";

export const incidentFeature: FeatureDefinition = {
  id: "incidents",
  label: "Incident Center",
  group: "Incident Center",
  path: "/incidents",
  routes: [
    {
      path: "",
      element: <IncidentCenterWorkspace />,
    },
  ],
};

export default incidentFeature;
