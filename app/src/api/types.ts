// TypeScript shapes for the API, copied from contracts/api.md ("Codes" and "Shapes").
// The fixtures in contracts/fixtures/ are the source of truth: if they change, change these too.
// JSON stays snake_case, exactly as the API sends it.

export type Language = "en" | "zu" | "xh";
export type Role = "customer" | "provider";
/** One of the 13 trade ids in data/glossary.json, for example "plumbing". */
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
/**
 * How a job is paid: in the app once it's done, a deposit once confirmed and the rest once done,
 * or cash off the app (Fixa never touches it).
 */
export type PaymentMethod = "in_app_after" | "in_app_split" | "cash";
export const PAYMENT_METHODS: PaymentMethod[] = ["in_app_after", "in_app_split", "cash"];

/** The trade ids in data/glossary.json, in merSETA/QCTO category order. */
export const TRADES: TradeId[] = [
  "electrical",
  "plumbing",
  "carpentry",
  "welding",
  "bricklaying",
  "mechanic",
  "roofing",
  "tiling",
  "cabinetmaking",
  "painting",
  "appliance_repair",
  "groundskeeping",
  "other",
];
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
  /** True for work only a licensed provider may do (geyser installs, electrical certificates). */
  needs_licence: boolean;
  distance_km: number;
  created_at: string;
};

/** Only the job's customer and its confirmed provider ever receive this. */
export type JobUnlocked = JobPublic & {
  address: string;
  directions: string | null;
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
  /** The ways the provider accepts payment. The customer picks one when accepting. */
  payment_methods: PaymentMethod[];
  /** The deposit, when in_app_split is offered (at most half the amount). */
  deposit_rands: number | null;
};

export type Message = {
  id: string;
  job_id: string;
  sender_id: string;
  /** Who it's for. A customer has one thread per quoting provider, and this says which. */
  recipient_id: string;
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

/** GET /api/record/summary (record_summary.json): what the "My record" screen shows. */
export type RecordSummary = {
  /** The trade the ARPL record is for, or null when none of the provider's trades has a toolkit. */
  arpl_trade: TradeId | null;
  /** Whole months from the first confirmed job in that trade to the last, as the ARPL PDF counts them. */
  experience_months: number;
  months_with_work: number;
  confirmed_jobs: number;
};

export type RecordExport = {
  verify_code: string;
  download_url: string;
  sha256: string;
};

/** A customer's few words about a provider. The server never says who wrote it. */
export type Vouch = {
  id: string;
  text: string;
  suburb: string;
  given_on: string;
};

export const REPORT_REASONS = ["illegal_work", "scam", "abuse", "fake_profile", "other"] as const;
export type ReportReason = (typeof REPORT_REASONS)[number];
export type ReportTargetType = "job" | "provider" | "message";

/** True when the server sent the unlocked job. The server decides; the app only reads what it got. */
export function isJobUnlocked(job: JobPublic | JobUnlocked): job is JobUnlocked {
  return "address" in job;
}
