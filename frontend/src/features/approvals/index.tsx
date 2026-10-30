import { FeatureDefinition } from "../../app/registry";

export const approvalsFeature: FeatureDefinition = {
  id: "approvals",
  label: "Approvals Queue",
  group: "Audit & Permissions",
  path: "/approvals",
  permissions: ["approvals:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Approvals Queue</h2>
          <p className="text-sm text-slate-400 mt-2">Manage pending Director approvals and proposals.</p>
        </div>
      ),
    },
  ],
};

export default approvalsFeature;
