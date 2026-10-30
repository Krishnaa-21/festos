import { FeatureDefinition } from "../../app/registry";

export const incidentsFeature: FeatureDefinition = {
  id: "incidents",
  label: "Incident Command Center",
  group: "Incident Center",
  path: "/incidents",
  permissions: ["incidents:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Incident Command Center</h2>
          <p className="text-sm text-slate-400 mt-2">Active disruption tracking, triage, and MTTR resolution logging.</p>
        </div>
      ),
    },
  ],
};

export default incidentsFeature;
