import type { FeatureDefinition } from "../../app/registry";
import { TransportSafetyWorkspace } from "./TransportSafetyWorkspace";

export const transportFeature: FeatureDefinition = {
  id: "transport",
  label: "Transportation & Safety",
  group: "Transportation",
  path: "/transport",
  routes: [
    {
      path: "",
      element: <TransportSafetyWorkspace />,
    },
  ],
};

export default transportFeature;
