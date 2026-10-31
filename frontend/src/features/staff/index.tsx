import { FeatureDefinition } from "../../app/registry";
import { StaffShiftsWorkspace } from "./StaffShiftsWorkspace";
import { Users } from "lucide-react";

export const staffFeature: FeatureDefinition = {
  id: "staff",
  label: "Staff & Shifts",
  group: "Staff & Shifts",
  path: "/staff",
  icon: Users,
  permissions: ["staff:read"],
  routes: [
    {
      path: "",
      element: <StaffShiftsWorkspace />,
    },
  ],
};

export default staffFeature;
