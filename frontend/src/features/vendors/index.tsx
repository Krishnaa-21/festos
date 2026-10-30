import { FeatureDefinition } from "../../app/registry";
import FoodVendorsWorkspace from "../food/FoodVendorsWorkspace";
import { Building } from "lucide-react";

export const vendorsFeature: FeatureDefinition = {
  id: "vendors",
  label: "Vendors",
  group: "Vendors & Food",
  path: "/vendors",
  icon: Building,
  permissions: ["vendors:read"],
  routes: [
    {
      path: "",
      element: <FoodVendorsWorkspace />,
    },
  ],
};

export default vendorsFeature;
