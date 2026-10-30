import { FeatureDefinition } from "../../app/registry";

export const impactFeature: FeatureDefinition = {
  id: "impact",
  label: "Downstream Impact Analysis",
  group: "Impact Analysis",
  path: "/impact",
  permissions: ["impact:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Impact Analysis</h2>
          <p className="text-sm text-slate-400 mt-2">Blast radius and downstream dependency cascade graph.</p>
        </div>
      ),
    },
  ],
};

export default impactFeature;
