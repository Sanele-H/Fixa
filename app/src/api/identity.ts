// ID checks for providers: the instant offline check of the number, then Home Affairs through Smile ID.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { accountKeys } from "./account";
import { postJson } from "./client";
import type { IdNumberCheck, IdResult } from "./types";

/**
 * POST /api/identity/verify. `consent` is always true: the screen only sends this after the
 * provider ticks the consent box (POPIA).
 */
export type IdVerification = {
  id_number: string;
  names: string;
};

/** POST /api/identity/check-number: the offline check, so a typo fails before any paid check. */
export function useCheckIdNumber() {
  return useMutation({
    mutationFn: (idNumber: string) => postJson<IdNumberCheck>("/api/identity/check-number", { id_number: idNumber }),
  });
}

/**
 * POST /api/identity/verify: checks the number and name with Home Affairs. The badge can go
 * up, so the logged-in user is fetched again. 429 after too many tries in a day, 503 when the
 * check is down.
 */
export function useVerifyIdentity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (verification: IdVerification) =>
      postJson<IdResult>("/api/identity/verify", { ...verification, consent: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: accountKeys.me }),
  });
}
