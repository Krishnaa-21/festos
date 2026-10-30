import { FeatureDefinition } from "../../app/registry";
import CheckInDesk from "./CheckInDesk";
import { UserCheck } from "lucide-react";

export const checkinFeature: FeatureDefinition = {
  id: "checkin",
  label: "Check-in Desk",
  group: "Check-in",
  path: "/checkin",
  icon: UserCheck,
  permissions: ["checkin:read"],
  routes: [
    {
      path: "",
      element: <CheckInDesk />,
    },
  ],
};

export default checkinFeature;
