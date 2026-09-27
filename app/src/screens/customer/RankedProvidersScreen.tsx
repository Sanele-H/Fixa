import { useTranslation } from "react-i18next";
import { generatePath, useParams } from "react-router";
import { PATHS } from "../../app/paths";
import { getTradeLabel } from "../../components/Badges";
import { ProviderCard } from "../../components/ProviderCard";
import { sampleJobPublic, sampleRankedProviders } from "../../dev/samples";
import { Screen, ScreenHeader, Slot } from "../../ui";

export default function RankedProvidersScreen() {
  const { t } = useTranslation();
  const { jobId = sampleJobPublic.id } = useParams();
  const job = sampleJobPublic;

  return (
    <Screen>
      <ScreenHeader
        backTo={generatePath(PATHS.job, { jobId })}
        eyebrow={`${getTradeLabel(t, job.trade)} · ${job.suburb}`}
        title={t("providers.title")}
        subtitle={t("providers.subtitle")}
      />

      <div className="stack">
        {sampleRankedProviders.map((provider) => (
          <ProviderCard key={provider.provider_id} provider={provider} />
        ))}
      </div>

      <Slot label="loading and empty states; how the customer waits for quotes" source="GET /api/jobs/{job_id}/providers" />
    </Screen>
  );
}
