import { FeatureDefinition } from "../../app/registry";
import ParticipantsPage from "./ParticipantsPage";
import { Users } from "lucide-react";

export const participantsFeature: FeatureDefinition = {
  id: "participants",
  label: "Participants Directory",
  group: "Participants",
  path: "/participants",
  icon: Users,
  permissions: ["participants:read"],
  routes: [
    {
      path: "",
      element: <ParticipantsPage />,
    },
  ],
};

export default participantsFeature;
