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
  nearby: "/nearby",
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
  camera: "/camera",
  // Development only
  devScreens: "/dev/screens",
} as const;

/**
 * A profile opened from the nearby list carries ?from=nearby, so its back arrow returns there
 * and it offers "Describe a job". Opened from a job's ranked list it carries ?job=<job id>, so
 * its back arrow returns to that list; the customer already has a job.
 */
export const PROFILE_FROM_PARAM = "from";
export const PROFILE_FROM_NEARBY = "nearby";
export const PROFILE_JOB_PARAM = "job";

/**
 * A customer has one chat thread per quoting provider, so their chat links carry
 * ?with=<provider id>. A provider has only one thread per job and needs no parameter.
 */
export const CHAT_WITH_PARAM = "with";

/**
 * The camera is opened from a job with ?jobId=<job id>&suburb=<suburb>: the suburb is stamped
 * on the photo and the back arrow returns to that job.
 */
export const CAMERA_JOB_PARAM = "jobId";
export const CAMERA_SUBURB_PARAM = "suburb";

/** The camera's link for a job, carrying the job id (for the back arrow) and its suburb (for the stamp). */
export function getCameraPath(jobId: string, suburb: string) {
  const searchParams = new URLSearchParams({ [CAMERA_JOB_PARAM]: jobId, [CAMERA_SUBURB_PARAM]: suburb });
  return `${PATHS.camera}?${searchParams}`;
}

/** The first tab each role lands on after login. */
export function getHomePath(role: Role) {
  return role === "provider" ? PATHS.feed : PATHS.home;
}
