import { FeatureDefinition } from "../../app/registry";
import { ReportsWorkspace } from "./ReportsWorkspace";

export const reportsFeature: FeatureDefinition = {
  id: "reports",
  label: "Section 14 Reports & Exports",
  group: "Reports",
  path: "/reports",
  permissions: ["reports:read"],
  routes: [
    {
      path: "",
      element: <ReportsWorkspace />,
    },
  ],
};

export default reportsFeature;
