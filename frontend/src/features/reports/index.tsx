import { FeatureDefinition } from "../../app/registry";

export const reportsFeature: FeatureDefinition = {
  id: "reports",
  label: "Section 14 Reports & Exports",
  group: "Reports",
  path: "/reports",
  permissions: ["reports:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Reports & Exports</h2>
          <p className="text-sm text-slate-400 mt-2">Downloadable CSV/MD reports catalog, post-festival report, and ZIP bundle.</p>
        </div>
      ),
    },
  ],
};

export default reportsFeature;
