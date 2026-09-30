import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

const API_URL = "http://localhost:8000";

// Matches --color-canvas in src/styles/tokens.css and the theme-color in index.html.
const CANVAS_COLOR = "#e7e7e4";

// Pages the server renders itself: the plain-HTML work record and verify pages opened from
// WhatsApp and SMS links, plus the API. The installed app must let these reach the server
// instead of answering with its own shell. The trailing slash keeps the app's /verify-id.
const SERVER_PAGE_PATTERNS = [/^\/api\//, /^\/record\//, /^\/verify\//];

// Shared dev setup from the build plan's "PWA gotchas" (team, Day 1 morning), plus the PWA.
// The service worker only runs in production builds (the plugin's default), so a dev server
// never serves a stale version. To try installing, run `npm run build` then `npm run preview`.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // A new deploy replaces the old version on the next visit, with no "update" prompt.
      registerType: "autoUpdate",
      manifest: {
        id: "/",
        name: "Fixa",
        short_name: "Fixa",
        description:
          "Hire someone nearby in your own language, without handing your number or address to a stranger.",
        lang: "en",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: CANVAS_COLOR,
        theme_color: CANVAS_COLOR,
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        navigateFallbackDenylist: SERVER_PAGE_PATTERNS,
        // Push notifications: shows them and opens the right screen on a tap (public/push-sw.js).
        importScripts: ["push-sw.js"],
      },
    }),
  ],
  // Read VITE_* settings from the repo-root .env.
  envDir: "..",
  server: {
    port: 5173,
    // The browser only talks to Vite. /api, and the plain-HTML work record and verify pages
    // (opened from share links and the PDF's QR code), are forwarded to FastAPI, so there are no
    // CORS problems and the links work over the tunnel. Keys starting with ^ are regular
    // expressions; the trailing slash keeps the app's own /verify-id.
    proxy: { "^/api/": API_URL, "^/record/": API_URL, "^/verify/": API_URL },
    // Phones need HTTPS for the camera, location and service worker: `npm run tunnel` from the repo root.
    allowedHosts: [".trycloudflare.com"],
  },
});
