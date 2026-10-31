import { FeatureDefinition } from "../../app/registry";
import { NotificationsWorkspace } from "./NotificationsWorkspace";
import { Bell } from "lucide-react";

export const notificationsFeature: FeatureDefinition = {
  id: "notifications",
  label: "Broadcast & Alerts",
  group: "Notifications",
  path: "/notifications",
  icon: Bell,
  permissions: ["notifications:read"],
  routes: [
    {
      path: "",
      element: <NotificationsWorkspace />,
    },
  ],
};

export default notificationsFeature;
