import { FeatureDefinition } from "../../app/registry";

export const premortemFeature: FeatureDefinition = {
  id: "premortem",
  label: "Fest Pre-Mortem",
  group: "Fest Pre-Mortem",
  path: "/premortem",
  permissions: ["premortem:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Fest Pre-Mortem Simulation</h2>
          <p className="text-sm text-slate-400 mt-2">Historical playback and hourly bottleneck prediction across the 4-day festival.</p>
        </div>
      ),
    },
  ],
};

export default premortemFeature;
