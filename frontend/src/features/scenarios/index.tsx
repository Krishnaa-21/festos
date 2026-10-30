import { FeatureDefinition } from "../../app/registry";

export const scenariosFeature: FeatureDefinition = {
  id: "scenarios",
  label: "Scenario Sandbox Simulator",
  group: "Scenario Simulator",
  path: "/scenarios",
  permissions: ["scenarios:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Scenario Simulator</h2>
          <p className="text-sm text-slate-400 mt-2">Isolated SQLite sandboxes to fork, mutate, compare, and safely commit changes.</p>
        </div>
      ),
    },
  ],
};

export default scenariosFeature;
