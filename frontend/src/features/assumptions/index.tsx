import { FeatureDefinition } from "../../app/registry";
import AssumptionsPage from "./AssumptionsPage";
import { Sliders } from "lucide-react";

export const assumptionsFeature: FeatureDefinition = {
  id: "assumptions",
  label: "Assumptions Register",
  group: "Overview",
  path: "/assumptions",
  icon: Sliders,
  permissions: ["assumptions:read"],
  routes: [
    {
      path: "",
      element: <AssumptionsPage />,
    },
  ],
};

export default assumptionsFeature;
