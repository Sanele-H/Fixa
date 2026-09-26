// The only file that talks to the backend. Screens import `api` and never call fetch themselves.
// Every function here matches one endpoint in docs/api-contract.md.
//
// VITE_USE_MOCK_API=true in .env swaps in fake data (mockData.js), so screens can be built
// before the backend is ready. Set it to false once Role 3's endpoints return real data.

import { mockApi } from "./mockData.js";

const API_BASE_PATH = "/api";
const DEMO_USER_HEADER = "X-User-Id";
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";

let currentUserId = null;

/** Remembers which demo user this phone is, so every request can send the X-User-Id header. */
export function setCurrentUserId(userId) {
  currentUserId = userId;
}

/** An error the backend answered with, e.g. 403 "contact details locked" or 501 "not built yet". */
export class ApiError extends Error {
  constructor(statusCode, detail) {
    super(detail);
    this.statusCode = statusCode;
  }
}

async function requestJson(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (currentUserId) {
    headers[DEMO_USER_HEADER] = currentUserId;
  }
  const response = await fetch(`${API_BASE_PATH}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorBody.detail ?? response.statusText);
  }
  return response.status === 204 ? null : response.json();
}

async function requestTradeSuggestion(photoFile, description) {
  const formData = new FormData();
  formData.append("photo", photoFile);
  const response = await fetch(
    `${API_BASE_PATH}/trade-suggestions?description=${encodeURIComponent(description)}`,
    { method: "POST", headers: { [DEMO_USER_HEADER]: currentUserId }, body: formData },
  );
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }
  return response.json();
}

const realApi = {
  listUsers: () => requestJson("GET", "/users"),
  getCurrentUser: () => requestJson("GET", "/users/me"),
  updateMyLanguage: (languageCode) => requestJson("PATCH", "/users/me", { preferredLanguage: languageCode }),
  listLanguages: () => requestJson("GET", "/languages"),
  listTrades: () => requestJson("GET", "/trades"),
  suggestTrade: requestTradeSuggestion,
  listJobs: () => requestJson("GET", "/jobs"),
  createJob: (newJob) => requestJson("POST", "/jobs", newJob),
  listQuotes: (jobId) => requestJson("GET", `/jobs/${jobId}/quotes`),
  createQuote: (jobId, newQuote) => requestJson("POST", `/jobs/${jobId}/quotes`, newQuote),
  acceptQuote: (jobId, quoteId) => requestJson("POST", `/jobs/${jobId}/accept`, { quoteId }),
  confirmJob: (jobId) => requestJson("POST", `/jobs/${jobId}/confirm`),
  unlockContactDetails: (jobId) => requestJson("POST", `/jobs/${jobId}/unlock`),
  getContactDetails: (jobId) => requestJson("GET", `/jobs/${jobId}/contact-details`),
  listMessages: (jobId, otherUserId) =>
    requestJson("GET", `/jobs/${jobId}/messages?with_user_id=${encodeURIComponent(otherUserId)}`),
  sendMessage: (jobId, recipientId, text) =>
    requestJson("POST", `/jobs/${jobId}/messages`, { recipientId, text }),
  resetDemo: () => requestJson("POST", "/demo/reset"),
};

export const api = USE_MOCK_API ? mockApi : realApi;

/** Always hits the real backend, even in mock mode, so you can see whether it's running. */
export const readBackendHealth = () => requestJson("GET", "/health");

export const isUsingMockApi = USE_MOCK_API;
