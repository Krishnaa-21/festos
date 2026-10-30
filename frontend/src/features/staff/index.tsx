import type { FeatureDefinition } from "../../app/registry";
import { StaffShiftsWorkspace } from "./StaffShiftsWorkspace";

export const staffFeature: FeatureDefinition = {
  id: "staff",
  label: "Staff & Shifts",
  group: "Staff & Shifts",
  path: "/staff",
  routes: [
    {
      path: "",
      element: <StaffShiftsWorkspace />,
    },
  ],
};

export default staffFeature;
