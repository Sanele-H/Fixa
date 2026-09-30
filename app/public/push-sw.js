// Shows Fixa's push notifications and opens the right screen when one is tapped.
// The built app's service worker imports this file (vite.config.ts, workbox.importScripts); on a
// dev server the app registers it on its own. It only handles pushes: no caching here.

self.addEventListener("push", (event) => {
  let data = { title: "Fixa", body: "", url: "/inbox" };
  try {
    data = { ...data, ...event.data.json() };
  } catch {
    // Not JSON: show whatever text came.
    data.body = event.data ? event.data.text() : "";
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: data.url },
      tag: data.url,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url ?? "/inbox", self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((client) => client.url.startsWith(self.location.origin));
      if (open) {
        return open.navigate(url).then((client) => client?.focus());
      }
      return self.clients.openWindow(url);
    }),
  );
});

// Take over straight away when registered on its own (dev), so the first push isn't missed.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
