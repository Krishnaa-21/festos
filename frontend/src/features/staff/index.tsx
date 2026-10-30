import { FeatureDefinition } from "../../app/registry";

export const staffFeature: FeatureDefinition = {
  id: "staff",
  label: "Staff & Shifts",
  group: "Staff & Shifts",
  path: "/staff",
  permissions: ["staff:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Staff Management</h2>
          <p className="text-sm text-slate-400 mt-2">Core team profiles, shift assignments, and volunteer demand coverage.</p>
        </div>
      ),
    },
  ],
};

export default staffFeature;
