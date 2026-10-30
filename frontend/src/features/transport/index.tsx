import { FeatureDefinition } from "../../app/registry";

export const transportFeature: FeatureDefinition = {
  id: "transport",
  label: "Transportation & Shuttles",
  group: "Transportation",
  path: "/transport",
  permissions: ["transport:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Duty-of-Care Transport Planner</h2>
          <p className="text-sm text-slate-400 mt-2">Shuttle runs schedule, night transit escort roster, and minor guardian verification queue.</p>
        </div>
      ),
    },
  ],
};

export default transportFeature;
