import { FeatureDefinition } from "../../app/registry";
import DecisionLogWorkspace from "./DecisionLogWorkspace";

export const decisionsFeature: FeatureDefinition = {
  id: "decisions",
  label: "Decision Log",
  group: "Decisions",
  path: "/decisions",
  routes: [
    {
      path: "",
      element: <DecisionLogWorkspace />,
    },
  ],
};

export default decisionsFeature;

