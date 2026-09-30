// Vouches: a few words from a customer who hired the provider. Shown on the profile and the work
// record, never with the writer's name.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, postJson } from "./client";
import type { Vouch } from "./types";

export const vouchKeys = {
  forProvider: (providerId: string) => ["providers", providerId, "vouches"] as const,
};

/** GET /api/providers/{provider_id}/vouches: newest first. */
export function useVouches(providerId: string) {
  return useQuery({
    queryKey: vouchKeys.forProvider(providerId),
    queryFn: () => getJson<Vouch[]>(`/api/providers/${providerId}/vouches`),
    enabled: Boolean(providerId),
  });
}

/** POST /api/providers/{provider_id}/vouches: a customer with a finished job, once per provider. */
export function useCreateVouch(providerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => postJson<Vouch>(`/api/providers/${providerId}/vouches`, { text }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: vouchKeys.forProvider(providerId) }),
  });
}
