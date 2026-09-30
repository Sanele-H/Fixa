// Logging in and the logged-in user: POST /api/auth/otp, POST /api/auth/verify, GET and PATCH /api/me.
// Screens read the user with useCurrentUser() from the session, not from here.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getJson, patchJson, postJson } from "./client";
import type { AuthResult, Language, User } from "./types";

export const accountKeys = {
  me: ["me"] as const,
};

type LoginCode = {
  phone: string;
  otp: string;
};

/** GET /api/me: who the stored token belongs to. The session calls this; screens use useCurrentUser(). */
export function readMe() {
  return getJson<User>("/api/me");
}

/** POST /api/auth/otp: asks for a login code. The demo sends no SMS; the code is always DEMO_OTP. */
export function useSendLoginCode() {
  return useMutation({
    mutationFn: (phone: string) => postJson<null>("/api/auth/otp", { phone }),
  });
}

/**
 * POST /api/auth/verify: swaps the phone number and code for a token and the user.
 * A wrong number or code is a 401. Pass the answer to the session's createSession().
 */
export function useVerifyLoginCode() {
  return useMutation({
    mutationFn: ({ phone, otp }: LoginCode) => postJson<AuthResult>("/api/auth/verify", { phone, otp }),
  });
}

/**
 * PATCH /api/me: saves the language on the account, so the server translates chats, jobs and
 * quotes into it. Updates the cached user with the answer. A GET /api/me already on its way is
 * cancelled first, so its older answer can't land after this one.
 */
export function useUpdateMyLanguage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (lang: Language) => patchJson<User>("/api/me", { lang }),
    onMutate: () => queryClient.cancelQueries({ queryKey: accountKeys.me }),
    onSuccess: (user) => queryClient.setQueryData(accountKeys.me, user),
  });
}
