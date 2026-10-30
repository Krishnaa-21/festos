import { FeatureDefinition } from "../../app/registry";
import UnknownsPage from "./UnknownsPage";
import { HelpCircle } from "lucide-react";

export const unknownsFeature: FeatureDefinition = {
  id: "unknowns",
  label: "Unknowns Burn-down",
  group: "Unknowns Burn-down",
  path: "/unknowns",
  icon: HelpCircle,
  permissions: ["participants:read"],
  routes: [
    {
      path: "",
      element: <UnknownsPage />,
    },
  ],
};

export default unknownsFeature;
