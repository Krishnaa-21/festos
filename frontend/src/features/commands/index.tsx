import { FeatureDefinition } from "../../app/registry";
import { CommandCenterWorkspace } from "./CommandCenterWorkspace";

export const commandsFeature: FeatureDefinition = {
  id: "commands",
  label: "AI Command Center",
  group: "AI Command Center",
  path: "/commands",
  permissions: ["commands:read"],
  routes: [
    {
      path: "",
      element: <CommandCenterWorkspace />,
    },
  ],
};

export default commandsFeature;
