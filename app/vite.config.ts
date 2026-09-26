import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API_URL = "http://localhost:8000";

// Shared dev setup from the build plan's "PWA gotchas" (team, Day 1 morning).
// P1 owns the rest of this file: add vite-plugin-pwa here (registerType "autoUpdate",
// service worker off in dev), plus anything the app itself needs.
export default defineConfig({
  plugins: [react()],
  // Read VITE_* settings from the repo-root .env.
  envDir: "..",
  server: {
    port: 5173,
    // The browser only talks to Vite; /api is forwarded to FastAPI, so there are no CORS problems.
    proxy: { "/api": API_URL },
    // Phones need HTTPS for the camera, location and service worker: `npm run tunnel` from the repo root.
    allowedHosts: [".trycloudflare.com"],
  },
});
