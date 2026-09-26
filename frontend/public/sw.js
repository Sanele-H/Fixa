// Minimal service worker: makes the app installable and loads the app shell on flaky signal.
// It never caches /api, so chat and job data are always live.
// Registered only in production builds (see src/main.jsx), so it can't serve stale code in dev.
// TODO (Role 2): decide whether an offline screen is worth it for the demo.

const APP_SHELL_CACHE_NAME = "fixa-shell-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(APP_SHELL_CACHE_NAME).then((cache) => cache.addAll(["/"])));
  self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);
  const isPageNavigation = event.request.mode === "navigate";
  if (!isPageNavigation || requestUrl.pathname.startsWith("/api")) {
    return;
  }
  event.respondWith(fetch(event.request).catch(() => caches.match("/")));
});
