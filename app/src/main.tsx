// Entry point for the PWA (P1). Loads the styles and the chosen language, then renders the router.
// Data comes from the API through TanStack Query (src/api/); the session sits inside it
// because it loads the user with a query.
// The service worker is registered by vite-plugin-pwa (see vite.config.ts), not from here.

import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
import { queryClient } from "./api/queryClient";
import { router } from "./app/router";
import { initI18n } from "./i18n";
import { SessionProvider } from "./session/SessionContext";
import "./styles/tokens.css";
import "./styles/base.css";
import "./ui/ui.css";

/** Mounts the app into #root. */
function renderApp() {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <SessionProvider>
          <RouterProvider router={router} />
        </SessionProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}

// Strings must be loaded before the first render, or screens would flash raw keys.
initI18n().then(renderApp);
