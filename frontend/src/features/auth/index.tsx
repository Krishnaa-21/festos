import { FeatureDefinition } from "../../app/registry";
import UserSessionsWorkspace from "./UserSessionsWorkspace";
import { Shield } from "lucide-react";

export const authFeature: FeatureDefinition = {
  id: "auth",
  label: "User Accounts & Sessions",
  group: "Audit & Permissions",
  path: "/auth/users",
  icon: Shield,
  permissions: ["audit:read"],
  routes: [
    {
      path: "",
      element: <UserSessionsWorkspace />,
    },
  ],
};

export default authFeature;
