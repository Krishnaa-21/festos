import { FeatureDefinition } from "../../app/registry";

export const forecastingFeature: FeatureDefinition = {
  id: "forecasting",
  label: "Demand Forecasting",
  group: "Overview",
  path: "/forecasting",
  permissions: ["forecasting:read"],
  routes: [
    {
      path: "",
      element: (
        <div className="p-8">
          <h2 className="text-xl font-bold text-white">Demand Forecasting</h2>
          <p className="text-sm text-slate-400 mt-2">Bed and resource load projections across the festival.</p>
        </div>
      ),
    },
  ],
};

export default forecastingFeature;
