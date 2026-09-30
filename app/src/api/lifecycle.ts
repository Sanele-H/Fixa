// A job's day and its follow-up: the provider checks in and out, the customer says it's done (or
// that nobody turned up), and two weeks later the customer says whether the fix is holding.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, postJson } from "./client";
import { invalidateJobLists, updateCachedJob } from "./jobs";
import { safetyKeys } from "./safety";
import type { JobPublic, JobUnlocked } from "./types";

type Job = JobPublic | JobUnlocked;

const FOLLOW_UPS_REFRESH_INTERVAL_MS = 60_000;

export const followUpKeys = {
  all: ["follow-ups"] as const,
};

/** POST /api/jobs/{job_id}/check-in: the provider has arrived (confirmed -> in progress). Call mutate(jobId). */
export function useCheckIn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => postJson<Job>(`/api/jobs/${jobId}/check-in`),
    onSuccess: (job) => {
      updateCachedJob(queryClient, job);
      // Checking in starts the provider's safety timer
      queryClient.invalidateQueries({ queryKey: safetyKeys.timer(job.id) });
    },
  });
}

/** POST /api/jobs/{job_id}/check-out: the provider says the work is finished. Call mutate(jobId). */
export function useCheckOut() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => postJson<Job>(`/api/jobs/${jobId}/check-out`),
    onSuccess: (job) => {
      updateCachedJob(queryClient, job);
      // Finishing the work stops it
      queryClient.invalidateQueries({ queryKey: safetyKeys.timer(job.id) });
    },
  });
}

/** What the customer tells us about the day: it was done, or the provider didn't turn up. */
export type FinishJob = {
  jobId: string;
  completed: boolean;
};

/** POST /api/jobs/{job_id}/done: the customer finishes the job. `completed: false` is a no-show. */
export function useFinishJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, completed }: FinishJob) => postJson<Job>(`/api/jobs/${jobId}/done`, { completed }),
    onSuccess: (job) => updateCachedJob(queryClient, job),
  });
}

/** GET /api/follow-ups: the customer's jobs finished two weeks ago or more, still waiting for "is it holding?". */
export function useFollowUps() {
  return useQuery({
    queryKey: followUpKeys.all,
    queryFn: () => getJson<Job[]>("/api/follow-ups"),
    refetchInterval: FOLLOW_UPS_REFRESH_INTERVAL_MS,
  });
}

/** What the customer answers two weeks on. */
export type StillWorkingAnswer = {
  jobId: string;
  stillWorking: boolean;
};

/** POST /api/jobs/{job_id}/still-working: one answer per job. It feeds the provider's trust range. */
export function useAnswerStillWorking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, stillWorking }: StillWorkingAnswer) =>
      postJson<Job>(`/api/jobs/${jobId}/still-working`, { still_working: stillWorking }),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: followUpKeys.all });
      updateCachedJob(queryClient, job);
      invalidateJobLists(queryClient);
    },
  });
}
