import { FeatureDefinition } from "../../app/registry";
import ExecutiveOverview from "./ExecutiveOverview";

export const dashboardFeature: FeatureDefinition = {
  id: "dashboard",
  label: "Executive Dashboard",
  group: "Overview",
  path: "/dashboard",
  routes: [
    {
      path: "",
      element: <ExecutiveOverview />,
    },
  ],
};

export default dashboardFeature;
