// Talks to the Fixa API. Paths are written in full ("/api/feed"), exactly as in
// contracts/api.md. They go to the page's own origin: in development Vite forwards /api to
// FastAPI, so the same code works on a laptop and on a phone through the tunnel.
//
// Every request carries the login token when there is one. A 401 on a request that sent the
// token means the server no longer accepts it (expired, or JWT_SECRET changed), so the token
// is dropped, and the session sends the person back to the login screen.
//
// Screens don't call these directly: they use the hooks in the other files of this folder.

import { deleteStoredToken, getStoredToken } from "../session/token";
import { ApiError, NO_ANSWER_STATUS, readErrorReason } from "./errors";

const UNAUTHORISED_STATUS = 401;
const NO_CONTENT_STATUS = 204;
const JSON_CONTENT_TYPE = "application/json";

/** Query string values. Undefined ones are left out, so optional filters can be passed as-is. */
export type QueryParams = Record<string, string | number | undefined>;

/** Adds the query string to a path, skipping undefined values: ("/api/providers", {trade: "plumbing"}). */
function buildUrl(path: string, params?: QueryParams): string {
  const searchParams = new URLSearchParams();
  for (const [name, value] of Object.entries(params ?? {})) {
    if (value !== undefined) {
      searchParams.set(name, String(value));
    }
  }
  const queryString = searchParams.toString();
  return queryString ? `${path}?${queryString}` : path;
}

/** The request's headers: the token when someone is logged in, and the body's type when it has one. */
function buildHeaders(token: string | null, contentType?: string): Headers {
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (contentType) {
    headers.set("Content-Type", contentType);
  }
  return headers;
}

/**
 * Drops the token after a 401, but only if it's still the token this request sent: a login
 * that happened while the request was on its way must not be undone.
 */
function deleteRejectedToken(sentToken: string | null) {
  if (sentToken && getStoredToken() === sentToken) {
    deleteStoredToken();
  }
}

/**
 * Sends one request and returns the response if it succeeded.
 * Throws an ApiError with the status and the server's reason when it didn't, or with
 * NO_ANSWER_STATUS when nothing came back (offline, or the server is down).
 */
async function sendRequest(url: string, init: RequestInit, contentType?: string): Promise<Response> {
  const sentToken = getStoredToken();
  let response: Response;
  try {
    response = await fetch(url, { ...init, headers: buildHeaders(sentToken, contentType) });
  } catch {
    throw new ApiError(NO_ANSWER_STATUS, "No answer from the server");
  }
  if (response.ok) {
    return response;
  }
  if (response.status === UNAUTHORISED_STATUS) {
    deleteRejectedToken(sentToken);
  }
  const { detail, code } = await readErrorReason(response);
  throw new ApiError(response.status, detail, code);
}

/** Reads a JSON body. A 204 has no body, so it reads as null. */
async function readJson<T>(response: Response): Promise<T> {
  if (response.status === NO_CONTENT_STATUS) {
    return null as T;
  }
  return (await response.json()) as T;
}

/** GET a JSON answer, for example getJson<JobPublic[]>("/api/feed"). */
export async function getJson<T>(path: string, params?: QueryParams): Promise<T> {
  return readJson<T>(await sendRequest(buildUrl(path, params), { method: "GET" }));
}

/** POST a JSON body (or none, for actions like /confirm) and read the JSON answer. */
export async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) };
  return readJson<T>(await sendRequest(path, init, body === undefined ? undefined : JSON_CONTENT_TYPE));
}

/** PATCH a JSON body and read the JSON answer. */
export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  return readJson<T>(await sendRequest(path, { method: "PATCH", body: JSON.stringify(body) }, JSON_CONTENT_TYPE));
}

/** PUT a JSON body (replace a whole thing, like the trusted contact) and read the JSON answer. */
export async function putJson<T>(path: string, body: unknown): Promise<T> {
  return readJson<T>(await sendRequest(path, { method: "PUT", body: JSON.stringify(body) }, JSON_CONTENT_TYPE));
}

/** DELETE something (a job) that answers 204 with no body. */
export async function deleteRequest(path: string): Promise<void> {
  await sendRequest(path, { method: "DELETE" });
}

/**
 * POST a multipart form (a photo upload) and read the JSON answer. No Content-Type is set:
 * the browser adds it with the multipart boundary.
 */
export async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  return readJson<T>(await sendRequest(path, { method: "POST", body: formData }));
}

/** GET a file that needs the token, such as a record PDF, using the path the server gave. */
export async function getBlob(path: string): Promise<Blob> {
  return (await sendRequest(path, { method: "GET" })).blob();
}
