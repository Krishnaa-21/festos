import type { FeatureDefinition } from "../../app/registry";
import { ImpactWorkspace } from "./ImpactWorkspace";

export const impactFeature: FeatureDefinition = {
  id: "impact",
  label: "Impact Analysis",
  group: "Impact Analysis",
  path: "/impact",
  routes: [
    {
      path: "",
      element: <ImpactWorkspace />,
    },
  ],
};

export default impactFeature;
