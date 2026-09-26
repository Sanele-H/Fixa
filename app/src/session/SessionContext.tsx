// A stand-in session so the right tabs show before login works.
// It only holds the role, remembered on this phone.
// P1: replace it with the token from POST /api/auth/verify and the user from GET /api/me.

import { createContext, useContext, useState, type ReactNode } from "react";
import type { Role } from "../api/types";

const ROLE_STORAGE_KEY = "fixa.role";
const DEFAULT_ROLE: Role = "customer";

/** Reads the stored role, or the default if there is none or storage is blocked. */
function getStoredRole(): Role {
  try {
    const storedValue = localStorage.getItem(ROLE_STORAGE_KEY);
    return storedValue === "provider" || storedValue === "customer" ? storedValue : DEFAULT_ROLE;
  } catch {
    return DEFAULT_ROLE;
  }
}

/** Remembers the role on this phone. Fails quietly if storage is blocked. */
function updateStoredRole(role: Role) {
  try {
    localStorage.setItem(ROLE_STORAGE_KEY, role);
  } catch {
    // The role still changes for this visit.
  }
}

type Session = {
  role: Role;
  updateRole: (role: Role) => void;
};

const SessionContext = createContext<Session | null>(null);

/** Holds the session for every screen under it. Wrap the router in this. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>(getStoredRole);

  function updateRole(nextRole: Role) {
    setRole(nextRole);
    updateStoredRole(nextRole);
  }

  return <SessionContext value={{ role, updateRole }}>{children}</SessionContext>;
}

/** Reads the current session. Throws if used outside SessionProvider, which is always a wiring bug. */
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) {
    throw new Error("useSession must be used inside <SessionProvider>");
  }
  return session;
}
