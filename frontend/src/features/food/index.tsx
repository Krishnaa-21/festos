import { FeatureDefinition } from "../../app/registry";
import FoodVendorsWorkspace from "./FoodVendorsWorkspace";
import { Utensils } from "lucide-react";

export const foodFeature: FeatureDefinition = {
  id: "food",
  label: "Vendors & Food",
  group: "Vendors & Food",
  path: "/food",
  icon: Utensils,
  permissions: ["food:read"],
  routes: [
    {
      path: "",
      element: <FoodVendorsWorkspace />,
    },
  ],
};

export default foodFeature;
