import { FeatureDefinition } from "../../app/registry";
import { AuditPage } from "./AuditPage";
import { ShieldCheck } from "lucide-react";

export const auditFeature: FeatureDefinition = {
  id: "audit",
  label: "Audit & Permissions",
  group: "Audit & Permissions",
  path: "/audit",
  icon: ShieldCheck,
  permissions: ["audit:read"],
  routes: [
    {
      path: "",
      element: <AuditPage />,
    },
  ],
};

export default auditFeature;
