// How a provider is shown in the ranked list and on their profile: job evidence and a trust
// range, never stars.

import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import type { Evidence, RankedProvider, Trust } from "../api/types";
import { PATHS } from "../app/paths";
import { formatDistanceKm, formatScoreOutOf100 } from "../format";
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

/** One provider in the ranked list. The whole card opens their profile. */
export function ProviderCard({ provider }: { provider: RankedProvider }) {
  const { t } = useTranslation();
  return (
    <CardLink to={generatePath(PATHS.provider, { providerId: provider.provider_id })} tone="raised">
      <div className="row row--between">
        <div className="row">
          <Avatar displayName={provider.display_name} />
          <div>
            <h2 className="section-title">{provider.display_name}</h2>
            <p className="small muted">{formatDistanceKm(provider.distance_km)}</p>
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
      <EvidenceStrip evidence={provider.evidence} />
      <ProviderTrust trust={provider.trust} />
    </CardLink>
  );
}
