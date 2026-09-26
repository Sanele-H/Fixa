// Entry point for the PWA (P1). Loads the styles and the chosen language, then renders the router.
// Still to add (P1): TanStack Query's QueryClientProvider, MSW in development, and
// vite-plugin-pwa (see vite.config.ts).

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";
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
      <SessionProvider>
        <RouterProvider router={router} />
      </SessionProvider>
    </StrictMode>,
  );
}

// Strings must be loaded before the first render, or screens would flash raw keys.
initI18n().then(renderApp);
