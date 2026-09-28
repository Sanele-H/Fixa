// Sample data straight from contracts/fixtures/, so every screen renders before the data layer exists.
// P1: replace each import of this file with a TanStack Query hook (served by MSW, then the real API),
// and delete this file once nothing imports it.

import feedFixture from "../../../contracts/fixtures/feed.json";
import idNumberCheckFixture from "../../../contracts/fixtures/id_number_check.json";
import jobIntentFixture from "../../../contracts/fixtures/job_intent.json";
import jobPublicFixture from "../../../contracts/fixtures/job_public.json";
import jobUnlockedFixture from "../../../contracts/fixtures/job_unlocked.json";
import meFixture from "../../../contracts/fixtures/me.json";
import messagesFixture from "../../../contracts/fixtures/messages.json";
import nearbyProvidersFixture from "../../../contracts/fixtures/nearby_providers.json";
import offAppJobFixture from "../../../contracts/fixtures/off_app_job.json";
import priceRangeFixture from "../../../contracts/fixtures/price_range.json";
import providerProfileFixture from "../../../contracts/fixtures/provider_profile.json";
import quotesFixture from "../../../contracts/fixtures/quotes.json";
import rankedProvidersFixture from "../../../contracts/fixtures/ranked_providers.json";
import recordExportFixture from "../../../contracts/fixtures/record_export.json";
import type {
  IdNumberCheck,
  JobIntent,
  JobPublic,
  JobUnlocked,
  Message,
  NearbyProvider,
  OffAppJob,
  PriceRange,
  ProviderProfile,
  Quote,
  RankedProvider,
  RecordExport,
  User,
} from "../api/types";

export const sampleMe = meFixture as User;
export const sampleFeed = feedFixture as JobPublic[];
export const sampleJobPublic = jobPublicFixture as JobPublic;
export const sampleJobUnlocked = jobUnlockedFixture as JobUnlocked;
export const sampleJobIntent = jobIntentFixture as JobIntent;
export const sampleRankedProviders = rankedProvidersFixture as RankedProvider[];
export const sampleProviderProfile = providerProfileFixture as ProviderProfile;
/** The answer to GET /api/providers?trade=plumbing for Lindiwe in Braamfontein (10 km). */
export const sampleNearbyProviders = nearbyProvidersFixture as NearbyProvider[];
export const sampleQuotes = quotesFixture as Quote[];
export const sampleMessages = messagesFixture as Message[];
export const samplePriceRange = priceRangeFixture as PriceRange;
export const sampleIdNumberCheck = idNumberCheckFixture as IdNumberCheck;
export const sampleOffAppJob = offAppJobFixture as OffAppJob;
export const sampleRecordExport = recordExportFixture as RecordExport;

/**
 * Months of experience on the "My record" screen. There is no endpoint for this yet
 * (contract gap), so this is the demo's "2 years 4 months".
 */
export const SAMPLE_EXPERIENCE_MONTHS = 28;
