// Jobs and quotes: describing and posting a job, the provider feed, quoting, and the state
// changes (accept, confirm, decline, cancel).
//
// Everything about one job is cached under ["jobs", jobId] (the job itself, and its quotes,
// ranked providers and messages below it), so invalidating that prefix refreshes the lot.

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { getJson, postJson } from "./client";
import type { MapPoint } from "./places";
import type { JobIntent, JobPublic, JobSize, JobUnlocked, Language, PriceRange, Quote, TradeId, Urgency } from "./types";

/** How often an open job and its quotes refresh, so the other phone's accept or confirm shows up. */
const JOB_REFRESH_INTERVAL_MS = 5_000;
/** How often the provider feed, and a person's own jobs, refresh while they're open. */
const FEED_REFRESH_INTERVAL_MS = 15_000;

export const jobKeys = {
  job: (jobId: string) => ["jobs", jobId] as const,
  quotes: (jobId: string) => ["jobs", jobId, "quotes"] as const,
  myJobs: ["my-jobs"] as const,
  feed: ["feed"] as const,
  priceRange: (trade?: TradeId, size?: JobSize, suburb?: string) => ["price-range", trade, size, suburb] as const,
};

/** POST /api/jobs/understand: the customer's own words, in their language. */
export type JobDescription = {
  text: string;
  lang: Language;
};

/** POST /api/jobs. `photo_id` comes from useUploadPhoto(). */
export type NewJob = {
  description: string;
  lang: Language;
  trade: TradeId;
  urgency: Urgency;
  size: JobSize;
  suburb: string;
  photo_id?: string;
  /** Insist on a licensed provider. The server also spots licensed work by itself. */
  needs_licence?: boolean;
  /** Optional free-text hints for the provider (gate code, landmark). Shown only after confirm. */
  directions?: string;
  /** A pin on the map when the job isn't at the customer's home. Left out: at their home. */
  location?: MapPoint;
};

/**
 * POST /api/jobs/{job_id}/quotes. `when` must carry a timezone, which toISOString() does:
 * new Date(pickedDateTime).toISOString().
 */
export type NewQuote = {
  amount_rands: number;
  when: string;
  message?: string;
};

/** Refreshes the lists a job shows up in: the feed and people's own jobs. */
export function invalidateJobLists(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: jobKeys.feed });
  queryClient.invalidateQueries({ queryKey: jobKeys.myJobs });
}

/** Puts the job the server just answered with into the cache, and refreshes everything under it and the lists. */
export function updateCachedJob(queryClient: QueryClient, job: JobPublic | JobUnlocked) {
  queryClient.setQueryData(jobKeys.job(job.id), job);
  queryClient.invalidateQueries({ queryKey: jobKeys.job(job.id) });
  invalidateJobLists(queryClient);
}

/** POST /api/jobs/understand: guesses the trade, urgency and size from a description (customer only). */
export function useUnderstandJob() {
  return useMutation({
    mutationFn: (description: JobDescription) => postJson<JobIntent>("/api/jobs/understand", description),
  });
}

/** POST /api/jobs: posts the job (customer only). The new job is cached, ready for its page. */
export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newJob: NewJob) => postJson<JobPublic>("/api/jobs", newJob),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.job(job.id), job);
      invalidateJobLists(queryClient);
    },
  });
}

/**
 * GET /api/jobs: a customer's own jobs, or the jobs a provider quoted on or was picked for,
 * newest first. Refreshes while it's open, so a provider sees an accepted quote arrive.
 */
export function useMyJobs() {
  return useQuery({
    queryKey: jobKeys.myJobs,
    queryFn: () => getJson<(JobPublic | JobUnlocked)[]>("/api/jobs"),
    refetchInterval: FEED_REFRESH_INTERVAL_MS,
  });
}

/**
 * GET /api/jobs/{job_id}: JobPublic, or JobUnlocked from `confirmed` on (check with
 * isJobUnlocked). Refreshes every few seconds while the screen is open.
 */
export function useJob(jobId: string) {
  return useQuery({
    queryKey: jobKeys.job(jobId),
    queryFn: () => getJson<JobPublic | JobUnlocked>(`/api/jobs/${jobId}`),
    refetchInterval: JOB_REFRESH_INTERVAL_MS,
  });
}

/** GET /api/jobs/{job_id}/quotes: every quote for the job's customer, or the provider's own. */
export function useJobQuotes(jobId: string) {
  return useQuery({
    queryKey: jobKeys.quotes(jobId),
    queryFn: () => getJson<Quote[]>(`/api/jobs/${jobId}/quotes`),
    refetchInterval: JOB_REFRESH_INTERVAL_MS,
  });
}

/** GET /api/feed: jobs near the provider that they can quote on (provider only). */
export function useFeed() {
  return useQuery({
    queryKey: jobKeys.feed,
    queryFn: () => getJson<JobPublic[]>("/api/feed"),
    refetchInterval: FEED_REFRESH_INTERVAL_MS,
  });
}

/**
 * GET /api/price-range: the usual accepted price for this kind of job nearby, or null when
 * there are too few quotes to say. Waits until trade, size and suburb are all known.
 */
export function usePriceRange(trade?: TradeId, size?: JobSize, suburb?: string) {
  return useQuery({
    queryKey: jobKeys.priceRange(trade, size, suburb),
    queryFn: () => getJson<PriceRange | null>("/api/price-range", { trade, size, suburb }),
    enabled: Boolean(trade && size && suburb),
  });
}

/** POST /api/jobs/{job_id}/quotes: sends a quote (provider only). 409 if the job stopped taking quotes. */
export function useCreateQuote(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newQuote: NewQuote) => postJson<Quote>(`/api/jobs/${jobId}/quotes`, newQuote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.job(jobId) });
      invalidateJobLists(queryClient);
    },
  });
}

/** A POST that moves a job to a new state and answers with the job. `buildPath` gets the mutation's id. */
function useJobStateChange(buildPath: (id: string) => string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postJson<JobPublic | JobUnlocked>(buildPath(id)),
    onSuccess: (job) => updateCachedJob(queryClient, job),
  });
}

/** POST /api/quotes/{quote_id}/accept: the customer picks a quote. Call mutate(quoteId). */
export function useAcceptQuote() {
  return useJobStateChange((quoteId) => `/api/quotes/${quoteId}/accept`);
}

/** POST /api/jobs/{job_id}/confirm: the accepted provider confirms, which unlocks contact details. Call mutate(jobId). */
export function useConfirmJob() {
  return useJobStateChange((jobId) => `/api/jobs/${jobId}/confirm`);
}

/** POST /api/jobs/{job_id}/decline: the accepted provider says no; the job goes back to quoting. Call mutate(jobId). */
export function useDeclineJob() {
  return useJobStateChange((jobId) => `/api/jobs/${jobId}/decline`);
}

/** POST /api/jobs/{job_id}/cancel: the customer cancels the job. Call mutate(jobId). */
export function useCancelJob() {
  return useJobStateChange((jobId) => `/api/jobs/${jobId}/cancel`);
}
