import { FeatureDefinition } from "../../app/registry";

export const overridesFeature: FeatureDefinition = {
  id: "overrides",
  label: "Override Register",
  group: "Audit & Permissions",
  path: "/overrides",
  permissions: ["overrides:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Override Register</h2>
          <p className="text-sm text-slate-400 mt-2">Active Director overrides and exception ledger with mandatory justification.</p>
        </div>
      ),
    },
  ],
};

export default overridesFeature;
