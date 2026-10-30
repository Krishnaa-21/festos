import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./index.css";

async function enableMocking() {
  if (import.meta.env.DEV) {
    try {
      const { worker } = await import("./mocks/browser");
      await worker.start({
        onUnhandledRequest: "bypass",
      });
    } catch (e) {
      console.warn("MSW browser worker failed to start, falling back to network:", e);
    }
  }
}

enableMocking().finally(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});

