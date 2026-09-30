// Safety during a job: the trusted contact, the panic button, the safety timer, and where each
// person's phone was at the job's key moments. See api/fixa_api/safety.py.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJson, postJson, putJson } from "./client";

const TIMER_REFRESH_INTERVAL_MS = 10_000;
const LOCATIONS_REFRESH_INTERVAL_MS = 15_000;
/** How long to wait for the phone's location before carrying on without it. */
const LOCATION_TIMEOUT_MS = 6_000;
/** A location up to a minute old is fine for "where was I when I checked in". */
const LOCATION_MAX_AGE_MS = 60_000;

export type TrustedContact = { name: string; phone: string };

export type SafetyTimerState = "running" | "safe" | "missed";
export type SafetyTimer = { id: string; state: SafetyTimerState; started_at: string; due_at: string };

export type KeyMoment = "check_in" | "check_out" | "done" | "panic" | "timer_start";
export type LocationEntry = {
  moment: KeyMoment;
  role: "customer" | "provider";
  name: string;
  is_me: boolean;
  at: string;
  distance_km: number;
};

export type PanicResult = {
  alert_id: string;
  contact: TrustedContact | null;
  location_shared: boolean;
  emergency_numbers: { label: string; number: string }[];
};

export type Place = { lat: number; lng: number; accuracy_m?: number };

export const safetyKeys = {
  contact: ["trusted-contact"] as const,
  timer: (jobId: string) => ["safety-timer", jobId] as const,
  locations: (jobId: string) => ["locations", jobId] as const,
};

/**
 * The phone's location, or null if the person says no, the phone can't tell, or it takes too
 * long. Never throws, so a safety action never waits on it for more than a few seconds.
 */
export function readPlace(): Promise<Place | null> {
  if (!("geolocation" in navigator)) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({ lat: position.coords.latitude, lng: position.coords.longitude, accuracy_m: position.coords.accuracy }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: LOCATION_TIMEOUT_MS, maximumAge: LOCATION_MAX_AGE_MS },
    );
  });
}

/**
 * Sends where the phone is at a key moment (check-in, finished, done, timer start), in the
 * background. Nothing waits for it and nothing breaks if the location isn't available.
 */
export function recordKeyMoment(jobId: string, moment: KeyMoment) {
  void readPlace().then((place) => {
    if (place) {
      postJson(`/api/jobs/${jobId}/location`, { moment, ...place }).catch(() => undefined);
    }
  });
}

/** GET /api/me/trusted-contact: {name, phone}, or null. */
export function useTrustedContact() {
  return useQuery({
    queryKey: safetyKeys.contact,
    queryFn: () => getJson<TrustedContact | null>("/api/me/trusted-contact"),
  });
}

/** PUT /api/me/trusted-contact. Call mutate({name, phone}). */
export function useSaveTrustedContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contact: TrustedContact) => putJson<TrustedContact>("/api/me/trusted-contact", contact),
    onSuccess: (contact) => queryClient.setQueryData(safetyKeys.contact, contact),
  });
}

/** POST /api/jobs/{job_id}/panic, with the phone's location when it can get it. Call mutate(jobId). */
export function usePanic() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (jobId: string) => {
      const place = await readPlace();
      return postJson<PanicResult>(`/api/jobs/${jobId}/panic`, place ?? {});
    },
    onSuccess: (_result, jobId) => {
      queryClient.invalidateQueries({ queryKey: safetyKeys.locations(jobId) });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

/** GET /api/jobs/{job_id}/safety-timer: the person's latest timer on this job, or null. */
export function useSafetyTimer(jobId: string) {
  return useQuery({
    queryKey: safetyKeys.timer(jobId),
    queryFn: () => getJson<SafetyTimer | null>(`/api/jobs/${jobId}/safety-timer`),
    refetchInterval: TIMER_REFRESH_INTERVAL_MS,
  });
}

/** POST /api/jobs/{job_id}/safety-timer. Call mutate(minutes). */
export function useStartSafetyTimer(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (minutes: number) => {
      recordKeyMoment(jobId, "timer_start");
      return postJson<SafetyTimer>(`/api/jobs/${jobId}/safety-timer`, { minutes });
    },
    onSuccess: (timer) => queryClient.setQueryData(safetyKeys.timer(jobId), timer),
  });
}

/** POST /api/jobs/{job_id}/safety-timer/safe: "I'm safe", which stops the timer. */
export function useSaySafe(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => postJson<SafetyTimer>(`/api/jobs/${jobId}/safety-timer/safe`),
    onSuccess: (timer) => queryClient.setQueryData(safetyKeys.timer(jobId), timer),
  });
}

/** GET /api/jobs/{job_id}/locations: each key moment and how far from the job it happened. */
export function useJobLocations(jobId: string) {
  return useQuery({
    queryKey: safetyKeys.locations(jobId),
    queryFn: () => getJson<LocationEntry[]>(`/api/jobs/${jobId}/locations`),
    refetchInterval: LOCATIONS_REFRESH_INTERVAL_MS,
  });
}
