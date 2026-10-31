import { FeatureDefinition } from "../../app/registry";
import FestPreMortemWorkspace from "./FestPreMortemWorkspace";

export const premortemFeature: FeatureDefinition = {
  id: "premortem",
  label: "Fest Pre-Mortem",
  group: "Fest Pre-Mortem",
  path: "/premortem",
  routes: [
    {
      path: "",
      element: <FestPreMortemWorkspace />,
    },
  ],
};

export default premortemFeature;

