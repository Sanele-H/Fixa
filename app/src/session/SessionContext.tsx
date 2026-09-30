// Who is logged in. The token from POST /api/auth/verify is kept on this phone (./token.ts),
// and the user comes from GET /api/me, so a reload stays logged in.
//
// Screens behind the login read the user with useCurrentUser(). The start screens and the
// router's guard (RequireSession in app/layouts.tsx) use useSession().

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useSyncExternalStore, type ReactNode } from "react";
import { accountKeys, readMe } from "../api/account";
import type { AuthResult, User } from "../api/types";
import { deleteStoredToken, getStoredToken, subscribeToToken, updateStoredToken } from "./token";

type Session = {
  /** The logged-in user, or null when nobody is logged in yet. */
  user: User | null;
  /** True while a token saved by an earlier visit is being checked with GET /api/me. */
  isCheckingToken: boolean;
  /** True when that check got no usable answer (offline, or the server is down). */
  hasTokenCheckFailed: boolean;
  /** Runs the check again, after it failed. */
  retryTokenCheck: () => void;
  /** Starts a session from POST /api/auth/verify's answer. */
  createSession: (authResult: AuthResult) => void;
  /** Ends the session. Forgetting the token also drops every cached answer (see api/queryClient.ts). */
  deleteSession: () => void;
};

const SessionContext = createContext<Session | null>(null);

/** Holds the session for every screen under it. Wrap the router in this, inside QueryClientProvider. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const token = useSyncExternalStore(subscribeToToken, getStoredToken);
  const hasToken = token !== null;
  // A 401 here drops the token (see api/client.ts), which sends the person back to login.
  const meQuery = useQuery({ queryKey: accountKeys.me, queryFn: readMe, enabled: hasToken });

  /**
   * Starts afresh for the new user: nothing cached from before, the user straight from the
   * login answer (no wait for GET /api/me), then the token, which lets the guarded screens open.
   */
  function createSession({ token: newToken, user }: AuthResult) {
    queryClient.clear();
    queryClient.setQueryData(accountKeys.me, user);
    updateStoredToken(newToken);
  }

  const session: Session = {
    user: hasToken ? (meQuery.data ?? null) : null,
    isCheckingToken: hasToken && meQuery.isPending,
    hasTokenCheckFailed: hasToken && meQuery.isError,
    retryTokenCheck: () => meQuery.refetch(),
    createSession,
    deleteSession: deleteStoredToken,
  };

  return <SessionContext value={session}>{children}</SessionContext>;
}

/** Reads the current session. Throws if used outside SessionProvider, which is always a wiring bug. */
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession must be used inside <SessionProvider>");
  }
  return session;
}

/**
 * The logged-in user, for screens behind the login. The router's RequireSession guard only
 * opens them once there is one, so this never returns null. Throws if used on a screen
 * outside the guard, which is always a routing bug.
 */
export function useCurrentUser(): User {
  const { user } = useSession();
  if (!user) {
    throw new Error("useCurrentUser must be used on a screen behind <RequireSession>");
  }
  return user;
}
