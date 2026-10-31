import { FeatureDefinition } from "../../app/registry";
import ApprovalsWorkspace from "./ApprovalsWorkspace";
import { CheckCircle2 } from "lucide-react";

export const approvalsFeature: FeatureDefinition = {
  id: "approvals",
  label: "Approvals Queue",
  group: "Audit & Permissions",
  path: "/approvals",
  icon: CheckCircle2,
  permissions: ["approvals:read"],
  routes: [
    {
      path: "",
      element: <ApprovalsWorkspace />,
    },
  ],
};

export default approvalsFeature;
