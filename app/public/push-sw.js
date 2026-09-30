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
      // One notification per job, replaced as updates arrive; renotify makes each update buzz
      // and sound again instead of swapping in silently.
      tag: data.url,
      renotify: true,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url ?? "/inbox", self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      const open = windows.find((client) => client.url.startsWith(self.location.origin));
      if (!open) {
        return self.clients.openWindow(url);
      }
      // navigate() only works on a window this worker controls, and can resolve null. Either
      // way, fall back to opening the screen in a new window so the tap always does something.
      return open
        .navigate(url)
        .then((client) => (client ? client.focus() : self.clients.openWindow(url)))
        .catch(() => self.clients.openWindow(url));
    }),
  );
});

// Take over straight away when registered on its own (dev), so the first push isn't missed.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
