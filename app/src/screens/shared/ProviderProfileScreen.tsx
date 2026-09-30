// A provider's public profile: evidence and a trust range, never stars.
// Opened from the nearby list (?from=nearby), its back arrow returns there and it offers
// "Describe a job", since customers hire through a job, never straight from a profile.
// Opened from a job's ranked list (?job=<job id>), its back arrow returns to that list.

import { useTranslation } from "react-i18next";
import { generatePath, useParams, useSearchParams } from "react-router";
import { useProviderProfile } from "../../api/providers";
import type { ProviderProfile, Role } from "../../api/types";
import { getHomePath, PATHS, PROFILE_FROM_NEARBY, PROFILE_FROM_PARAM, PROFILE_JOB_PARAM } from "../../app/paths";
import { IdBadgeChip, TradeChip } from "../../components/Badges";
import { DescribeJobCard } from "../../components/DescribeJobCard";
import { ReportButton } from "../../components/ReportButton";
import { VouchList } from "../../components/VouchList";
import { LoadError, LoadingNote } from "../../components/LoadState";
import { EVIDENCE_KEYS, formatSpokenLanguages, ProviderTrust } from "../../components/ProviderCard";
import { formatDistanceKm } from "../../format";
import { useCurrentUser } from "../../session/SessionContext";
import { Avatar, Card, Chip, IconButton, Screen, ScreenHeader, Stat } from "../../ui";

/** Where the back arrow goes: the nearby list, the job's ranked list, or the home tab. */
function getBackPath(searchParams: URLSearchParams, role: Role) {
  const fromJobId = searchParams.get(PROFILE_JOB_PARAM);
  if (searchParams.get(PROFILE_FROM_PARAM) === PROFILE_FROM_NEARBY) {
    return PATHS.nearby;
  }
  return fromJobId ? generatePath(PATHS.jobProviders, { jobId: fromJobId }) : getHomePath(role);
}

/** Who they are, their trust range and their evidence. */
function ProfileDetails({ provider }: { provider: ProviderProfile }) {
  const { t } = useTranslation();
  const isMe = useCurrentUser().id === provider.provider_id;
  return (
    <>

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

      <VouchList providerId={provider.provider_id} />
      {!isMe && <ReportButton targetType="provider" targetId={provider.provider_id} />}
    </>
  );
}

export default function ProviderProfileScreen() {
  const { t } = useTranslation();
  const { role } = useCurrentUser();
  const { providerId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const isFromNearby = searchParams.get(PROFILE_FROM_PARAM) === PROFILE_FROM_NEARBY;
  const profile = useProviderProfile(providerId);
  const provider = profile.data;

  return (
    <Screen>
      <ScreenHeader
        backTo={getBackPath(searchParams, role)}
        actions={<IconButton icon="share" label={t("profile.share")} />}
        eyebrow={provider && `${provider.suburb} · ${formatDistanceKm(provider.distance_km)}`}
        title={provider?.display_name ?? t("role.provider")}
      />
      {profile.isPending && <LoadingNote />}
      {profile.isError && <LoadError error={profile.error} onRetry={() => profile.refetch()} />}
      {provider && <ProfileDetails provider={provider} />}
      {isFromNearby && role === "customer" && <DescribeJobCard hint={t("nearby.describeHint")} />}
    </Screen>
  );
}
