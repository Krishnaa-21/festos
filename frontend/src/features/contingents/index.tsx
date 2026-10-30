import { FeatureDefinition } from "../../app/registry";
import ContingentsPage from "./ContingentsPage";
import { Building2 } from "lucide-react";

export const contingentsFeature: FeatureDefinition = {
  id: "contingents",
  label: "Contingents Matrix",
  group: "Contingents",
  path: "/contingents",
  icon: Building2,
  permissions: ["contingents:read"],
  routes: [
    {
      path: "",
      element: <ContingentsPage />,
    },
  ],
};

export default contingentsFeature;
