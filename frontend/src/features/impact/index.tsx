import { FeatureDefinition } from "../../app/registry";
import { ImpactWorkspace } from "./ImpactWorkspace";
import { GitFork } from "lucide-react";

export const impactFeature: FeatureDefinition = {
  id: "impact",
  label: "Downstream Impact Analysis",
  group: "Impact Analysis",
  path: "/impact",
  icon: GitFork,
  permissions: ["impact:read"],
  routes: [
    {
      path: "",
      element: <ImpactWorkspace />,
    },
  ],
};

export default impactFeature;
