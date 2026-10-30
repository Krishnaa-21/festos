import { FeatureDefinition } from "../../app/registry";
import EventsVenuesWorkspace from "./EventsVenuesWorkspace";
import { Calendar } from "lucide-react";

export const eventsFeature: FeatureDefinition = {
  id: "events",
  label: "Events & Venues",
  group: "Events & Venues",
  path: "/events",
  icon: Calendar,
  permissions: ["events:read"],
  routes: [
    {
      path: "",
      element: <EventsVenuesWorkspace />,
    },
    {
      path: "venues",
      element: <EventsVenuesWorkspace />,
    },
    {
      path: "schedule",
      element: <EventsVenuesWorkspace />,
    },
  ],
};

export default eventsFeature;
