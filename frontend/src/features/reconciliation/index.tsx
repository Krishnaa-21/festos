import { FeatureDefinition } from "../../app/registry";
import ReconciliationPage from "./ReconciliationPage";
import { GitMerge } from "lucide-react";

export const reconciliationFeature: FeatureDefinition = {
  id: "reconciliation",
  label: "Data Reconciliation",
  group: "Data Reconciliation",
  path: "/reconciliation",
  icon: GitMerge,
  permissions: ["reconciliation:read"],
  routes: [
    {
      path: "",
      element: <ReconciliationPage />,
    },
  ],
};

export default reconciliationFeature;
