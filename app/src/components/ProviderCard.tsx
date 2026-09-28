// How a provider is shown in the ranked list, on the nearby list and on their profile: job
// evidence and a trust range, never stars.

import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import type { Evidence, Language, NearbyProvider, RankedProvider, Trust } from "../api/types";
import { PATHS, PROFILE_FROM_NEARBY, PROFILE_FROM_PARAM } from "../app/paths";
import { formatDistanceKm, formatScoreOutOf100 } from "../format";
import { LANGUAGE_NAMES } from "../i18n";
import { Avatar, CardLink, Chip, TrustRange } from "../ui";
import { IdBadgeChip, TradeChip } from "./Badges";

/** The evidence counts in the order they're shown. */
export const EVIDENCE_KEYS: (keyof Evidence)[] = ["jobs", "repeat_customers", "photos", "off_app_confirmed"];

/** "9 jobs · 2 repeat customers · 14 photos · 3 off-app jobs" as four small tiles. */
export function EvidenceStrip({ evidence }: { evidence: Evidence }) {
  const { t } = useTranslation();
  return (
    <ul className="evidence-strip">
      {EVIDENCE_KEYS.map((key) => (
        <li key={key} className="evidence-strip__item">
          <span className="evidence-strip__value">{evidence[key]}</span>
          <span className="evidence-strip__label">{t(`evidence.${key}`, { count: evidence[key] })}</span>
        </li>
      ))}
    </ul>
  );
}

/** The trust range with its words: the API's label, the range as "74–93", and a screen-reader sentence. */
export function ProviderTrust({ trust }: { trust: Trust }) {
  const { t } = useTranslation();
  if (trust.low === null || trust.high === null) {
    return <TrustRange {...trust} description={trust.label} />;
  }
  const lowOutOf100 = formatScoreOutOf100(trust.low);
  const highOutOf100 = formatScoreOutOf100(trust.high);
  return (
    <TrustRange
      {...trust}
      rangeText={`${lowOutOf100}–${highOutOf100}`}
      description={t("trust.rangeDescription", { low: lowOutOf100, high: highOutOf100, label: trust.label })}
    />
  );
}

type ProviderCardTopProps = {
  provider: Pick<RankedProvider, "display_name" | "trades" | "is_newcomer" | "id_badge">;
  /** The line under the name: "1.8 km" in the ranked list, "Parktown · 1.8 km" when browsing. */
  whereText: string;
};

/** The top of every provider card: avatar, name, where they are, the New tag, trade and ID chips. */
function ProviderCardTop({ provider, whereText }: ProviderCardTopProps) {
  const { t } = useTranslation();
  return (
    <>
      <div className="row row--between">
        <div className="row">
          <Avatar displayName={provider.display_name} />
          <div>
            <h2 className="section-title">{provider.display_name}</h2>
            <p className="small muted">{whereText}</p>
          </div>
        </div>
        {provider.is_newcomer && <Chip tone="lime">{t("providers.newcomer")}</Chip>}
      </div>
      <div className="row">
        {provider.trades.map((trade) => (
          <TradeChip key={trade} trade={trade} tone="outline" />
        ))}
        <IdBadgeChip badge={provider.id_badge} />
      </div>
    </>
  );
}

/** One provider in the ranked list. The whole card opens their profile. */
export function ProviderCard({ provider }: { provider: RankedProvider }) {
  return (
    <CardLink to={generatePath(PATHS.provider, { providerId: provider.provider_id })} tone="raised">
      <ProviderCardTop provider={provider} whereText={formatDistanceKm(provider.distance_km)} />
      <EvidenceStrip evidence={provider.evidence} />
      <ProviderTrust trust={provider.trust} />
    </CardLink>
  );
}

/** "isiZulu, English" for the "Speaks …" line, with each language's name in that language. */
export function formatSpokenLanguages(languages: Language[]) {
  return languages.map((language) => LANGUAGE_NAMES[language]).join(", ");
}

/**
 * One provider on the "Who works near you" list: the same card as the ranked list, plus the
 * languages they speak, and no trust range, so browsing never ranks people before a job exists.
 * Opens their profile with ?from=nearby, so the profile's back arrow comes back here.
 */
export function NearbyProviderCard({ provider }: { provider: NearbyProvider }) {
  const { t } = useTranslation();
  const profilePath = generatePath(PATHS.provider, { providerId: provider.provider_id });
  return (
    <CardLink to={`${profilePath}?${PROFILE_FROM_PARAM}=${PROFILE_FROM_NEARBY}`} tone="raised">
      <ProviderCardTop
        provider={provider}
        whereText={`${provider.suburb} · ${formatDistanceKm(provider.distance_km)}`}
      />
      <p className="small muted">{t("profile.speaks", { languages: formatSpokenLanguages(provider.langs) })}</p>
      <EvidenceStrip evidence={provider.evidence} />
    </CardLink>
  );
}
