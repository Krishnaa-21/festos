import { FeatureDefinition } from "../../app/registry";
import AccommodationWorkspace from "./AccommodationWorkspace";
import { Building } from "lucide-react";

export { ParticipantAccommodationTab } from "./ParticipantAccommodationTab";

export const accommodationFeature: FeatureDefinition = {
  id: "accommodation",
  label: "Accommodation",
  group: "Accommodation",
  path: "/accommodation",
  icon: Building,
  permissions: ["accommodation:read"],
  routes: [
    {
      path: "",
      element: <AccommodationWorkspace />,
    },
  ],
};

export default accommodationFeature;
