import type { FeatureDefinition } from "../../app/registry";
import { NotificationsWorkspace } from "./NotificationsWorkspace";

export const notificationsFeature: FeatureDefinition = {
  id: "notifications",
  label: "Notifications Broadcast",
  group: "Notifications",
  path: "/notifications",
  routes: [
    {
      path: "",
      element: <NotificationsWorkspace />,
    },
  ],
};

export default notificationsFeature;
