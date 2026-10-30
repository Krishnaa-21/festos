import { setupWorker } from "msw/browser";
import { incidentHandlers } from "../test/incidents_msw";

export const worker = setupWorker(...incidentHandlers);
