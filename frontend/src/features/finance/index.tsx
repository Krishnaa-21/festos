import { FeatureDefinition } from "../../app/registry";
import FinanceWorkspace from "./FinanceWorkspace";
import { DollarSign } from "lucide-react";

export const financeFeature: FeatureDefinition = {
  id: "finance",
  label: "Finance",
  group: "Finance",
  path: "/finance",
  icon: DollarSign,
  permissions: ["finance:read"],
  routes: [
    {
      path: "",
      element: <FinanceWorkspace />,
    },
  ],
};

export default financeFeature;
