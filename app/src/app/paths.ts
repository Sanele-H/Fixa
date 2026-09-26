// Every screen's URL. Each screen has its own link so it can be shared (for example on WhatsApp).
// Build links with react-router's generatePath, e.g. generatePath(PATHS.job, { jobId }).
//
// The server owns /api/*, /record/{provider_id} and /verify/{code} (plain-HTML link pages),
// so app paths must never start with those. That's why the record screen is /my-record.

import type { Role } from "../api/types";

export const PATHS = {
  start: "/",
  welcome: "/welcome",
  login: "/login",
  // Customer
  home: "/home",
  newJob: "/jobs/new",
  jobProviders: "/jobs/:jobId/providers",
  // Customer and provider
  job: "/jobs/:jobId",
  jobChat: "/jobs/:jobId/chat",
  provider: "/providers/:providerId",
  me: "/me",
  // Provider
  feed: "/feed",
  jobQuote: "/jobs/:jobId/quote",
  verifyId: "/verify-id",
  offAppJob: "/off-app-jobs/new",
  myRecord: "/my-record",
  // Development only
  devScreens: "/dev/screens",
} as const;

/** The first tab each role lands on after login. */
export function getHomePath(role: Role) {
  return role === "provider" ? PATHS.feed : PATHS.home;
}
