// The inbox behind the bell, and push notifications on the phone's lock screen.
// See api/fixa_api/notifications.py and push.py.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "./errors";
import { getJson, postJson } from "./client";

const INBOX_REFRESH_INTERVAL_MS = 15_000;
const NOT_FOUND_STATUS = 404;

export type InboxItem = {
  id: string;
  kind: string;
  title: string;
  body: string;
  job_id: string | null;
  created_at: string;
  read: boolean;
};

export type Inbox = { unread: number; items: InboxItem[] };

export const notificationKeys = {
  inbox: ["notifications"] as const,
};

/** GET /api/notifications: newest first, already in the reader's language. Refreshes by itself. */
export function useInbox() {
  return useQuery({
    queryKey: notificationKeys.inbox,
    queryFn: () => getJson<Inbox>("/api/notifications"),
    refetchInterval: INBOX_REFRESH_INTERVAL_MS,
  });
}

/** POST /api/notifications/read: marks everything read. */
export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => postJson<Inbox>("/api/notifications/read"),
    onSuccess: (inbox) => queryClient.setQueryData(notificationKeys.inbox, inbox),
  });
}

/** POST /api/notifications/{id}/read. Call mutate(id). */
export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => postJson<Inbox>(`/api/notifications/${notificationId}/read`),
    onSuccess: (inbox) => queryClient.setQueryData(notificationKeys.inbox, inbox),
  });
}

/** Whether this browser can do push at all (iPhones only in the installed app). */
export function canUsePush() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export type PushOutcome = "on" | "denied" | "unavailable" | "not_set_up";

/** The key the push service wants: the base64url VAPID key as bytes. */
function toKeyBytes(base64Url: string) {
  const base64 = (base64Url + "=".repeat((4 - (base64Url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
}

/**
 * The service worker that shows pushes. The built app's own worker imports push-sw.js; a dev
 * server has none (on purpose, so nothing goes stale), so push-sw.js is registered on its own.
 */
async function getPushWorker() {
  if (import.meta.env.DEV) {
    return navigator.serviceWorker.register("/push-sw.js");
  }
  return navigator.serviceWorker.ready;
}

/** Asks permission, subscribes this browser and tells the server. */
export async function turnOnPush(): Promise<PushOutcome> {
  if (!canUsePush()) {
    return "unavailable";
  }
  let publicKey: string;
  try {
    publicKey = (await getJson<{ public_key: string }>("/api/push/key")).public_key;
  } catch (error) {
    if (error instanceof ApiError && error.status === NOT_FOUND_STATUS) {
      return "not_set_up";
    }
    throw error;
  }
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return "denied";
  }
  const worker = await getPushWorker();
  const subscription =
    (await worker.pushManager.getSubscription()) ??
    (await worker.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: toKeyBytes(publicKey) }));
  await postJson("/api/push/subscriptions", subscription.toJSON());
  return "on";
}

/**
 * True when this browser already agreed and has a subscription. The subscription is sent to the
 * server again each time, so push keeps working after a different login on this phone or a
 * database reset (the server replaces the old copy).
 */
export async function isPushOn(): Promise<boolean> {
  if (!canUsePush() || Notification.permission !== "granted") {
    return false;
  }
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration?.pushManager.getSubscription();
  if (!subscription) {
    return false;
  }
  await postJson("/api/push/subscriptions", subscription.toJSON());
  return true;
}
