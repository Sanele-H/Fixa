// "Who can help": the fair ranked list for one of the customer's jobs, newcomer slot included.
// Customers don't pick from here: people nearby see the job and quote, and the customer
// chooses from the quotes on the job page.

import { useTranslation } from "react-i18next";
import { generatePath, useParams } from "react-router";
import { useJob } from "../../api/jobs";
import { useRankedProviders } from "../../api/providers";
import { PATHS } from "../../app/paths";
import { getTradeLabel } from "../../components/Badges";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { ProviderCard } from "../../components/ProviderCard";
import { ButtonLink, Card, Screen, ScreenHeader } from "../../ui";

/** The ranked providers, with loading, error and empty states. */
function RankedList({ jobId }: { jobId: string }) {
  const { t } = useTranslation();
  const rankedProviders = useRankedProviders(jobId);

  if (rankedProviders.isPending) {
    return <LoadingNote />;
  }
  if (rankedProviders.isError) {
    return <LoadError error={rankedProviders.error} onRetry={() => rankedProviders.refetch()} />;
  }
  if (rankedProviders.data.length === 0) {
    return <EmptyNote title={t("providers.emptyTitle")}>{t("providers.emptyBody")}</EmptyNote>;
  }
  return rankedProviders.data.map((provider) => (
    <ProviderCard key={provider.provider_id} provider={provider} fromJobId={jobId} />
  ));
}

export default function RankedProvidersScreen() {
  const { t } = useTranslation();
  const { jobId = "" } = useParams();
  const job = useJob(jobId);
  const jobPath = generatePath(PATHS.job, { jobId });

  return (
    <Screen>
      <ScreenHeader
        backTo={jobPath}
        eyebrow={job.data && `${getTradeLabel(t, job.data.trade)} · ${job.data.suburb}`}
        title={t("providers.title")}
        subtitle={t("providers.subtitle")}
      />

      <Card tone="lavender">
        <p className="section-title">{t("providers.waitingTitle")}</p>
        <p className="small">{t("providers.waitingBody")}</p>
        <ButtonLink to={jobPath} variant="secondary" isSmall>
          {t("providers.openJob")}
        </ButtonLink>
      </Card>

      <div className="stack">
        <RankedList jobId={jobId} />
      </div>
    </Screen>
  );
}
