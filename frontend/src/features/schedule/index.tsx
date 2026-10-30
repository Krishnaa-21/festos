import { FeatureDefinition } from "../../app/registry";
import EventsVenuesWorkspace from "../events/EventsVenuesWorkspace";
import { Calendar } from "lucide-react";

export const scheduleFeature: FeatureDefinition = {
  id: "schedule",
  label: "Schedule",
  group: "Events & Venues",
  path: "/schedule",
  icon: Calendar,
  permissions: ["events:read"],
  routes: [
    {
      path: "",
      element: <EventsVenuesWorkspace />,
    },
  ],
};

export default scheduleFeature;
