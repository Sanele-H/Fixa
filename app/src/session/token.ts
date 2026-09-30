// The login token from POST /api/auth/verify, kept on this phone so a reload stays logged in.
// It lives in a tiny store instead of React state, so the API client can read it outside
// components, and the session re-renders when it changes (see useSyncExternalStore in
// SessionContext.tsx).

const TOKEN_STORAGE_KEY = "fixa.token";

type TokenListener = () => void;

const tokenListeners = new Set<TokenListener>();

/**
 * Reads the token an earlier visit saved, or null if there is none.
 * Storage can throw (private mode, blocked site data), which counts as "logged out".
 */
function readSavedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** This visit's copy of the token. It still works when storage is blocked; it just isn't kept. */
let currentToken: string | null = readSavedToken();

/** Tells everyone listening that the token changed. */
function notifyTokenListeners() {
  tokenListeners.forEach((listener) => listener());
}

/** Returns the token for the Authorization header, or null when nobody is logged in. */
export function getStoredToken(): string | null {
  return currentToken;
}

/** Keeps a new token (after a login) and tells every listener. */
export function updateStoredToken(token: string) {
  currentToken = token;
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // The session still works for this visit; the next visit asks to log in again.
  }
  notifyTokenListeners();
}

/** Forgets the token (log out, or the server no longer accepts it) and tells every listener. */
export function deleteStoredToken() {
  currentToken = null;
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Nothing to remove if storage is blocked.
  }
  notifyTokenListeners();
}

/** Calls `listener` after every token change. Returns the function that stops listening. */
export function subscribeToToken(listener: TokenListener) {
  tokenListeners.add(listener);
  return () => {
    tokenListeners.delete(listener);
  };
}
