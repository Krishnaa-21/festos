import { FeatureDefinition } from "../../app/registry";
import ImportsPage from "./ImportsPage";
import { UploadCloud } from "lucide-react";

export const importsFeature: FeatureDefinition = {
  id: "imports",
  label: "Import & Data Quality",
  group: "Data Reconciliation",
  path: "/imports",
  icon: UploadCloud,
  permissions: ["reconciliation:read"],
  routes: [
    {
      path: "",
      element: <ImportsPage />,
    },
  ],
};

export default importsFeature;
