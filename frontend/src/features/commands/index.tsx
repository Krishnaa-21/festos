import { FeatureDefinition } from "../../app/registry";

export const commandsFeature: FeatureDefinition = {
  id: "commands",
  label: "Natural Language Command Bar",
  group: "AI Command Center",
  path: "/commands",
  permissions: ["commands:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">AI Command Bar</h2>
          <p className="text-sm text-slate-400 mt-2">Natural-language command parse and execution console.</p>
        </div>
      ),
    },
  ],
};

export default commandsFeature;
