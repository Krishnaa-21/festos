import { FeatureDefinition } from "../../app/registry";

export const authFeature: FeatureDefinition = {
  id: "auth",
  label: "User Accounts & Sessions",
  group: "Audit & Permissions",
  path: "/auth/users",
  permissions: ["audit:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">User Accounts & Sessions</h2>
          <p className="text-sm text-slate-400 mt-2">Manage operational roles and active sessions.</p>
        </div>
      ),
    },
  ],
};

export default authFeature;
