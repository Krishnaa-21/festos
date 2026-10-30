import { setupWorker } from "msw/browser";
import { incidentHandlers } from "../test/incidents_msw";
import { insightHandlers } from "../test/insight_msw";

export const worker = setupWorker(...incidentHandlers, ...insightHandlers);
