import { FeatureDefinition } from "../../app/registry";
import MerchandiseWorkspace from "./MerchandiseWorkspace";
import { ShoppingBag } from "lucide-react";

export const merchandiseFeature: FeatureDefinition = {
  id: "merchandise",
  label: "Merchandise",
  group: "Merchandise",
  path: "/merchandise",
  icon: ShoppingBag,
  permissions: ["merchandise:read"],
  routes: [
    {
      path: "",
      element: <MerchandiseWorkspace />,
    },
    {
      path: "counter",
      element: <MerchandiseWorkspace />,
    },
  ],
};

export default merchandiseFeature;
