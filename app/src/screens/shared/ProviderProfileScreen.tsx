// A provider's public profile: evidence and a trust range, never stars.
// Opened from the nearby list (?from=nearby), its back arrow returns there and it offers
// "Describe a job", since customers hire through a job, never straight from a profile.

import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import { getHomePath, PATHS, PROFILE_FROM_NEARBY, PROFILE_FROM_PARAM } from "../../app/paths";
import { IdBadgeChip, TradeChip } from "../../components/Badges";
import { DescribeJobCard } from "../../components/DescribeJobCard";
import { EVIDENCE_KEYS, formatSpokenLanguages, ProviderTrust } from "../../components/ProviderCard";
import { sampleProviderProfile } from "../../dev/samples";
import { formatDistanceKm } from "../../format";
import { useSession } from "../../session/SessionContext";
import { Avatar, Card, Chip, IconButton, Screen, ScreenHeader, Slot, Stat } from "../../ui";

export default function ProviderProfileScreen() {
  const { t } = useTranslation();
  const { role } = useSession();
  const [searchParams] = useSearchParams();
  const isFromNearby = searchParams.get(PROFILE_FROM_PARAM) === PROFILE_FROM_NEARBY;
  const provider = sampleProviderProfile;

  return (
    <Screen>
      <ScreenHeader
        backTo={isFromNearby ? PATHS.nearby : getHomePath(role)}
        actions={<IconButton icon="share" label={t("profile.share")} />}
        eyebrow={`${provider.suburb} · ${formatDistanceKm(provider.distance_km)}`}
        title={provider.display_name}
      />

      <Card tone="raised">
        <div className="row row--nowrap">
          <Avatar displayName={provider.display_name} isLarge />
          <div className="stack stack--tight">
            <div className="row">
              {provider.trades.map((trade) => (
                <TradeChip key={trade} trade={trade} tone="outline" />
              ))}
            </div>
            <div className="row">
              <IdBadgeChip badge={provider.id_badge} />
              {provider.is_newcomer && <Chip tone="lime">{t("providers.newcomer")}</Chip>}
            </div>
          </div>
        </div>
        <p>{provider.bio}</p>
        <p className="small muted">{t("profile.speaks", { languages: formatSpokenLanguages(provider.langs) })}</p>
      </Card>

      <Card tone="inverse">
        <p className="eyebrow">{t("trust.title")}</p>
        <ProviderTrust trust={provider.trust} />
        <p className="small muted">{t("trust.explainer")}</p>
      </Card>

      <div className="grid-2">
        {EVIDENCE_KEYS.map((key) => (
          <Card key={key} tone="raised">
            <Stat value={provider.evidence[key]} label={t(`evidence.${key}`, { count: provider.evidence[key] })} />
          </Card>
        ))}
      </div>

      <Slot label="before/after work photos, vouches, report button" source="contract gap: the profile has no photo list yet" minHeightPx={120} />

      {isFromNearby && role === "customer" && <DescribeJobCard hint={t("nearby.describeHint")} />}
    </Screen>
  );
}
