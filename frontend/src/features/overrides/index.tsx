import { FeatureDefinition } from "../../app/registry";
import OverridesWorkspace from "./OverridesWorkspace";
import { ShieldAlert } from "lucide-react";

export const overridesFeature: FeatureDefinition = {
  id: "overrides",
  label: "Override Register",
  group: "Audit & Permissions",
  path: "/overrides",
  icon: ShieldAlert,
  permissions: ["overrides:read"],
  routes: [
    {
      path: "",
      element: <OverridesWorkspace />,
    },
  ],
};

export default overridesFeature;
