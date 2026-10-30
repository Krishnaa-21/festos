import { FeatureDefinition } from "../../app/registry";
import EventsVenuesWorkspace from "../events/EventsVenuesWorkspace";
import { MapPin } from "lucide-react";

export const venuesFeature: FeatureDefinition = {
  id: "venues",
  label: "Venues",
  group: "Events & Venues",
  path: "/venues",
  icon: MapPin,
  permissions: ["events:read"],
  routes: [
    {
      path: "",
      element: <EventsVenuesWorkspace />,
    },
  ],
};

export default venuesFeature;
