// Providers: a job's ranked list, the "Who works near you" list, and a provider's profile.

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getJson } from "./client";
import type { Language, NearbyProvider, ProviderProfile, RankedProvider, TradeId } from "./types";

export const providerKeys = {
  /** Under the job's key (see jobs.ts), so it refreshes with the job. */
  ranked: (jobId: string) => ["jobs", jobId, "providers"] as const,
  nearby: (filters: NearbyFilters) => ["providers", "nearby", filters] as const,
  profile: (providerId: string) => ["providers", providerId] as const,
};

/**
 * GET /api/providers filters. `lang` keeps only providers who speak it; leave it out for anyone.
 * `radius_km` defaults to 10 on the server and must be above 0 and at most 30.
 */
export type NearbyFilters = {
  trade: TradeId;
  lang?: Language;
  radius_km?: number;
};

/** GET /api/jobs/{job_id}/providers: the fair ranked list for the job's customer, newcomer slot included. */
export function useRankedProviders(jobId: string) {
  return useQuery({
    queryKey: providerKeys.ranked(jobId),
    queryFn: () => getJson<RankedProvider[]>(`/api/jobs/${jobId}/providers`),
  });
}

/**
 * GET /api/providers: who does a trade near the customer, nearest first, with no trust (customer only).
 * While a new filter loads, the previous list stays on screen instead of flashing empty.
 */
export function useNearbyProviders(filters: NearbyFilters) {
  return useQuery({
    queryKey: providerKeys.nearby(filters),
    queryFn: () => getJson<NearbyProvider[]>("/api/providers", filters),
    placeholderData: keepPreviousData,
  });
}

/** GET /api/providers/{provider_id}: the profile, with evidence and the trust range. */
export function useProviderProfile(providerId: string) {
  return useQuery({
    queryKey: providerKeys.profile(providerId),
    queryFn: () => getJson<ProviderProfile>(`/api/providers/${providerId}`),
  });
}
