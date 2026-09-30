// TypeScript shapes for the API, copied from contracts/api.md ("Codes" and "Shapes").
// The fixtures in contracts/fixtures/ are the source of truth: if they change, change these too.
// JSON stays snake_case, exactly as the API sends it.

export type Language = "en" | "zu" | "xh";
export type Role = "customer" | "provider";
/** One of the 11 trade ids in data/glossary.json, for example "plumbing". */
export type TradeId = string;
export type JobSize = "small" | "medium" | "large";
export type Urgency = "low" | "normal" | "urgent";
export type JobState =
  | "posted"
  | "quoting"
  | "quote_accepted"
  | "confirmed"
  | "in_progress"
  | "done"
  | "followed_up"
  | "cancelled";
export type QuoteState = "open" | "accepted" | "declined" | "withdrawn";
export type IdBadge = "none" | "id_number" | "home_affairs";
export type RecordMode = "arpl" | "statement";

/** The trade ids in data/glossary.json so far (2 of the 11). P1: add each one as P3 adds it. */
export const TRADES: TradeId[] = ["plumbing", "electrical"];
export const JOB_SIZES: JobSize[] = ["small", "medium", "large"];
export const URGENCIES: Urgency[] = ["low", "normal", "urgent"];

/** The job states in order, for the progress ruler. `cancelled` can happen at any point, so it is not in the line. */
export const JOB_STATE_ORDER: JobState[] = [
  "posted",
  "quoting",
  "quote_accepted",
  "confirmed",
  "in_progress",
  "done",
  "followed_up",
];

export type User = {
  id: string;
  role: Role;
  display_name: string;
  lang: Language;
  suburb: string;
  id_badge: IdBadge;
};

/** POST /api/auth/verify: the token for the Authorization header, and who logged in. */
export type AuthResult = {
  token: string;
  user: User;
};

/** What everyone sees before `confirmed`: the suburb and the problem, never the address or phones. */
export type JobPublic = {
  id: string;
  state: JobState;
  trade: TradeId;
  size: JobSize;
  urgency: Urgency;
  suburb: string;
  problem: string;
  problem_original: string;
  problem_lang: Language;
  translation_flagged: boolean;
  photo_url: string | null;
  distance_km: number;
  created_at: string;
};

/** Only the job's customer and its confirmed provider ever receive this. */
export type JobUnlocked = JobPublic & {
  address: string;
  customer_phone: string;
  provider_phone: string;
  provider_photo_url: string | null;
};

export type Evidence = {
  jobs: number;
  repeat_customers: number;
  photos: number;
  off_app_confirmed: number;
};

/** Trust score and range, 0–1. All null for a newcomer. `label` arrives already translated. */
export type Trust = {
  score: number | null;
  low: number | null;
  high: number | null;
  label: string;
};

export type RankedProvider = {
  provider_id: string;
  display_name: string;
  trades: TradeId[];
  distance_km: number;
  is_newcomer: boolean;
  id_badge: IdBadge;
  evidence: Evidence;
  trust: Trust;
};

export type ProviderProfile = RankedProvider & {
  suburb: string;
  langs: Language[];
  bio: string;
};

/**
 * One provider on the "Who works near you" list. No trust, on purpose: browsing is for
 * looking, so the list must not turn into a leaderboard. Trust shows on the profile.
 */
export type NearbyProvider = Omit<RankedProvider, "trust"> & {
  suburb: string;
  langs: Language[];
};

export type Quote = {
  id: string;
  job_id: string;
  provider_id: string;
  amount_rands: number;
  when: string;
  message: string | null;
  state: QuoteState;
  created_at: string;
};

export type Message = {
  id: string;
  job_id: string;
  sender_id: string;
  text: string;
  original: string;
  original_lang: Language;
  flagged: boolean;
  flag_reason: string | null;
  contacts_hidden: boolean;
  scam_warnings: string[];
  sent_at: string;
};

export type PriceRange = {
  trade: TradeId;
  size: JobSize;
  suburb: string;
  low_rands: number;
  high_rands: number;
  n_quotes: number;
};

export type JobIntent = {
  trade: TradeId;
  urgency: Urgency;
  size: JobSize;
  confidence: number;
};

export type IdNumberCheck = {
  valid: boolean;
  reason: string | null;
  date_of_birth: string | null;
};

/** POST /api/identity/verify (id_result.json). `tier` is the badge this check earned. */
export type IdResult = {
  tier: Exclude<IdBadge, "none">;
  verified: boolean;
  name_match: boolean;
  provider: string;
  reference: string;
  checked_at: string;
};

/** POST /api/photos (photo.json). Send `photo_id` with the job; `url` is a signed link for <img>. */
export type Photo = {
  photo_id: string;
  url: string;
};

export type OffAppJob = {
  id: string;
  state: string;
  trade_task: string;
  date: string;
  suburb: string;
  amount_rands: number | null;
};

export type RecordExport = {
  verify_code: string;
  download_url: string;
  sha256: string;
};

/** True when the server sent the unlocked job. The server decides; the app only reads what it got. */
export function isJobUnlocked(job: JobPublic | JobUnlocked): job is JobUnlocked {
  return "address" in job;
}
