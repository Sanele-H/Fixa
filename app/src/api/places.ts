// Places on the map, for a customer choosing where a job is: their own area (to open the map on)
// and the name of a pin they dropped. The name comes from the server, which asks OpenStreetMap
// at most once a second for everyone, so the app only asks when the pin stops moving.

import { useQuery } from "@tanstack/react-query";
import { getJson } from "./client";

/** A point on the map, in degrees. */
export type MapPoint = {
  lat: number;
  lng: number;
};

/** GET /api/me/area: the customer's home suburb, and its point rounded to about a kilometre. */
export type MyArea = MapPoint & {
  suburb: string;
};

/** GET /api/places/reverse: what a pin is called. `label` is the street address providers see once confirmed. */
export type PinnedPlace = {
  suburb: string;
  label: string;
};

/** Pins within about 11 m share one lookup, the same rounding the server caches by. */
const PLACE_KEY_DECIMALS = 4;
/** A place's name doesn't change, so a looked-up pin stays fresh for the whole visit. */
const PLACE_STALE_TIME_MS = Infinity;

export const placeKeys = {
  myArea: ["my-area"] as const,
  place: (point: MapPoint) =>
    ["place", point.lat.toFixed(PLACE_KEY_DECIMALS), point.lng.toFixed(PLACE_KEY_DECIMALS)] as const,
};

/** GET /api/me/area: where to open the job map (customer only). */
export function useMyArea() {
  return useQuery({
    queryKey: placeKeys.myArea,
    queryFn: () => getJson<MyArea>("/api/me/area"),
    staleTime: PLACE_STALE_TIME_MS,
  });
}

/** GET /api/places/reverse: names the pin, or waits while there's no pin yet. 422 outside South Africa. */
export function usePinnedPlace(point: MapPoint | null) {
  return useQuery({
    queryKey: point ? placeKeys.place(point) : ["place", "none"],
    queryFn: () => getJson<PinnedPlace>("/api/places/reverse", { lat: point!.lat, lng: point!.lng }),
    enabled: point !== null,
    staleTime: PLACE_STALE_TIME_MS,
    retry: false,
  });
}
