import { FeatureDefinition } from "../../app/registry";
import ForecastingWorkspace from "./ForecastingWorkspace";

export const forecastingFeature: FeatureDefinition = {
  id: "forecasting",
  label: "Forecasting",
  group: "Forecasting",
  path: "/forecasting",
  routes: [
    {
      path: "",
      element: <ForecastingWorkspace />,
    },
  ],
};

export default forecastingFeature;

