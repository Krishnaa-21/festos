import { FeatureDefinition } from "../../app/registry";

export const notificationsFeature: FeatureDefinition = {
  id: "notifications",
  label: "Broadcast & Alerts",
  group: "Overview",
  path: "/notifications",
  permissions: ["notifications:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Broadcast & Alerts</h2>
          <p className="text-sm text-slate-400 mt-2">Operational notification drafts and critical broadcast dispatch.</p>
        </div>
      ),
    },
  ],
};

export default notificationsFeature;
