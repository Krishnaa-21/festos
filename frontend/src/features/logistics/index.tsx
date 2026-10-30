import { FeatureDefinition } from "../../app/registry";
import LogisticsWorkspace from "./LogisticsWorkspace";
import { Package } from "lucide-react";

export const logisticsFeature: FeatureDefinition = {
  id: "logistics",
  label: "Logistics",
  group: "Logistics",
  path: "/logistics",
  icon: Package,
  permissions: ["logistics:read"],
  routes: [
    {
      path: "",
      element: <LogisticsWorkspace />,
    },
  ],
};

export default logisticsFeature;
