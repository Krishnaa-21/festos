import { FeatureDefinition } from "../../app/registry";

export const decisionsFeature: FeatureDefinition = {
  id: "decisions",
  label: "Decision Log & Why Cards",
  group: "Overview",
  path: "/decisions",
  permissions: ["decisions:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Decision Log</h2>
          <p className="text-sm text-slate-400 mt-2">Historical decision cards with full constraint explainability.</p>
        </div>
      ),
    },
  ],
};

export default decisionsFeature;
