// The app's one TanStack Query client: what it caches, when it retries, and the clean slate
// when a session ends.

import { QueryClient } from "@tanstack/react-query";
import { getStoredToken, subscribeToToken } from "../session/token";
import { isRetryableError } from "./errors";

/** Retries after a read fails: enough to ride out the API restarting while someone saves a file. */
const MAX_READ_RETRIES = 2;

/** Retries a failed read only when that could help (no answer, or a 5xx), never after a 4xx. */
function shouldRetryRead(failureCount: number, error: unknown) {
  return isRetryableError(error) && failureCount < MAX_READ_RETRIES;
}

/**
 * Reads are fetched again whenever a screen opens or the app comes back to the front, which
 * keeps two phones in step during a demo. Writes (mutations) are never retried, so a quote or
 * a message can't be sent twice.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: shouldRetryRead },
  },
});

// When the token goes (log out, or the server rejected it), drop every cached answer, so the
// next person on this phone never sees the last person's jobs, chats or contact details.
subscribeToToken(() => {
  if (getStoredToken() === null) {
    queryClient.clear();
  }
});
