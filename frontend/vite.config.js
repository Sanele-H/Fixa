import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const BACKEND_URL = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  // Read VITE_* settings from the repo-root .env, next to the backend's settings.
  envDir: "..",
  server: {
    // Listen on the Wi-Fi network too, so both demo phones can open http://<laptop-ip>:5173
    host: true,
    port: 5173,
    // The phones only talk to Vite; Vite forwards /api to the backend on the laptop.
    proxy: { "/api": BACKEND_URL },
  },
});
