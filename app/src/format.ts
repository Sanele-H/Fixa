// Formatting for numbers, money, distances and dates.
// Prices, times and phone numbers are never translated, only laid out for the reader's locale.

import type { Language } from "./api/types";

/** Intl locale for each app language. South African English groups thousands with a space (R1 200). */
const LOCALE_BY_LANGUAGE: Record<Language, string> = {
  en: "en-ZA",
  zu: "zu-ZA",
  xh: "xh-ZA",
};

const SCORE_SCALE = 100;

/** Picks the Intl locale for an app language, falling back to South African English. */
function getLocale(language: string) {
  return LOCALE_BY_LANGUAGE[language as Language] ?? LOCALE_BY_LANGUAGE.en;
}

/** "R450", "R1 200". Whole rands only: the API sends whole numbers. */
export function formatRands(amountRands: number, language: string) {
  return `R${amountRands.toLocaleString(getLocale(language))}`;
}

const DISTANCE_DECIMAL_PLACES = 1;

/**
 * "2.4 km". One decimal, since the server already rounds distances for privacy.
 * Always a decimal point: Intl's en-ZA would print "2,4", but the plan and contract use "2.4 km".
 */
export function formatDistanceKm(distanceKm: number) {
  return `${distanceKm.toFixed(DISTANCE_DECIMAL_PLACES)} km`;
}

/** "Tue 29 Sep, 10:00" in the reader's locale. */
export function formatDateTime(isoDateTime: string, language: string) {
  return new Intl.DateTimeFormat(getLocale(language), {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(isoDateTime));
}

/** "10:00" in the reader's locale, for chat messages. */
export function formatTime(isoDateTime: string, language: string) {
  return new Intl.DateTimeFormat(getLocale(language), { hour: "2-digit", minute: "2-digit" }).format(
    new Date(isoDateTime),
  );
}

/** "14 Aug 2026" in the reader's locale, for dates with no time. */
export function formatDate(isoDate: string, language: string) {
  return new Intl.DateTimeFormat(getLocale(language), { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(isoDate),
  );
}

/** Turns a 0–1 trust value into a whole number out of 100, for text like "74–93". */
export function formatScoreOutOf100(score: number) {
  return Math.round(score * SCORE_SCALE);
}
