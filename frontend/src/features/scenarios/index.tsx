import { FeatureDefinition } from "../../app/registry";
import ScenarioSimulatorWorkspace from "./ScenarioSimulatorWorkspace";

export const scenariosFeature: FeatureDefinition = {
  id: "scenarios",
  label: "Scenario Simulator",
  group: "Scenario Simulator",
  path: "/scenarios",
  routes: [
    {
      path: "",
      element: <ScenarioSimulatorWorkspace />,
    },
  ],
};

export default scenariosFeature;
