import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "../components/layout/AppShell";
import { getRegisteredFeatures } from "./registry";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  const features = getRegisteredFeatures();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Navigate to="/dashboard" replace />} />

            {/* Dynamically mounted feature routes */}
            {features.map((feature) => (
              <React.Fragment key={feature.id}>
                {feature.routes && feature.routes.length > 0 ? (
                  feature.routes.map((r, idx) => (
                    <Route
                      key={`${feature.id}-${idx}`}
                      path={`${feature.path.replace(/^\//, "")}/${r.path}`.replace(/\/$/, "")}
                      element={r.element}
                    />
                  ))
                ) : (
                  <Route
                    path={feature.path.replace(/^\//, "")}
                    element={
                      <div className="p-8">
                        <h2 className="text-xl font-bold text-white">{feature.label}</h2>
                        <p className="text-sm text-slate-400 mt-2">
                          Feature scaffold ready. Implemented in respective team prompt.
                        </p>
                      </div>
                    }
                  />
                )}
              </React.Fragment>
            ))}

            {/* Fallback route */}
            <Route
              path="*"
              element={
                <div className="p-8 text-center">
                  <h2 className="text-xl font-bold text-white">404 - Not Found</h2>
                  <p className="text-sm text-slate-400 mt-2">The requested view does not exist.</p>
                </div>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
