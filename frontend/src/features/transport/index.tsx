import { FeatureDefinition } from "../../app/registry";
import { TransportSafetyWorkspace } from "./TransportSafetyWorkspace";
import { Truck } from "lucide-react";

export const transportFeature: FeatureDefinition = {
  id: "transport",
  label: "Transportation & Shuttles",
  group: "Transportation",
  path: "/transport",
  icon: Truck,
  permissions: ["transport:read"],
  routes: [
    {
      path: "",
      element: <TransportSafetyWorkspace />,
    },
  ],
};

export default transportFeature;
