// Failed requests: the error the API client throws, and which message a screen shows for it.
// The server's own `detail` text is English only, so screens show a translated message
// picked by status instead (getErrorMessageKey), and the detail is kept for debugging.

/** The status an ApiError has when no answer came back: offline, or the server is down. */
export const NO_ANSWER_STATUS = 0;

const SERVER_ERROR_MIN_STATUS = 500;

/** A request the server refused, or never answered. */
export class ApiError extends Error {
  /** The HTTP status, or NO_ANSWER_STATUS when there was no answer at all. */
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * FastAPI's error body: one sentence, a list of problems when the input was invalid (422), or
 * an object some routes send (POST /api/identity/verify: {error, reason}).
 */
type ErrorBody = {
  detail?: string | { msg?: string }[] | Record<string, unknown>;
};

/**
 * Reads the server's reason from a failed response: the `detail` sentence, the first problem
 * in a 422 list, or an object detail as JSON. Falls back to the status line when the body isn't
 * FastAPI's JSON (for example Vite's proxy answering while the API restarts).
 */
export async function readErrorDetail(response: Response): Promise<string> {
  const fallbackDetail = `${response.status} ${response.statusText}`.trim();
  try {
    const { detail } = (await response.json()) as ErrorBody;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail[0]?.msg ?? fallbackDetail;
    }
    return detail ? JSON.stringify(detail) : fallbackDetail;
  } catch {
    return fallbackDetail;
  }
}

/**
 * True when trying again could help: no answer, or a server error (5xx), such as the API
 * restarting while someone saves a file. Never for 4xx, where the answer won't change.
 */
export function isRetryableError(error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }
  return error.status === NO_ANSWER_STATUS || error.status >= SERVER_ERROR_MIN_STATUS;
}

/** The i18n keys getErrorMessageKey can return. Each one is in locales/en.json under "errors". */
export type ErrorMessageKey =
  | "errors.offline"
  | "errors.signedOut"
  | "errors.notAllowed"
  | "errors.notFound"
  | "errors.changed"
  | "errors.invalid"
  | "errors.tooMany"
  | "errors.generic";

const ERROR_MESSAGE_KEYS_BY_STATUS: Record<number, ErrorMessageKey> = {
  [NO_ANSWER_STATUS]: "errors.offline",
  401: "errors.signedOut",
  403: "errors.notAllowed",
  404: "errors.notFound",
  409: "errors.changed",
  422: "errors.invalid",
  429: "errors.tooMany",
};

/**
 * Picks the translated message for a failed request, by its status. Use it as
 * `t(getErrorMessageKey(error))`. A screen that knows better for one status (the login screen
 * for 401, say) checks `error.status` itself first.
 */
export function getErrorMessageKey(error: unknown): ErrorMessageKey {
  if (!(error instanceof ApiError)) {
    return "errors.generic";
  }
  return ERROR_MESSAGE_KEYS_BY_STATUS[error.status] ?? "errors.generic";
}
