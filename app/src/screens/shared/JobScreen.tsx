// One job, seen by its customer or a provider. Contact details show only if the server sent
// them (JobUnlocked, from `confirmed` on).

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams, useSearchParams } from "react-router";
import { getHomePath, PATHS } from "../../app/paths";
import { getTradeLabel, TradeChip } from "../../components/Badges";
import { ContactCard } from "../../components/ContactCard";
import { JobStateRuler } from "../../components/JobStateRuler";
import { QuoteCard } from "../../components/QuoteCard";
import { sampleJobPublic, sampleJobUnlocked, sampleQuotes, sampleRankedProviders } from "../../dev/samples";
import { formatDistanceKm } from "../../format";
import { useSession } from "../../session/SessionContext";
import { Banner, Button, Card, Chip, IconLink, Screen, ScreenHeader, Slot } from "../../ui";

/** Sample switch until the data layer exists: /jobs/job_001?preview=confirmed shows the unlocked job. */
const PREVIEW_PARAM = "preview";
const PREVIEW_CONFIRMED = "confirmed";

/** Finds a provider's display name in the sample list, falling back to their id. */
function getSampleProviderName(providerId: string) {
  return sampleRankedProviders.find((provider) => provider.provider_id === providerId)?.display_name ?? providerId;
}

export default function JobScreen() {
  const { t } = useTranslation();
  const { role } = useSession();
  const { jobId = sampleJobPublic.id } = useParams();
  const [searchParams] = useSearchParams();
  const [isShowingOriginal, setIsShowingOriginal] = useState(false);
  const job = searchParams.get(PREVIEW_PARAM) === PREVIEW_CONFIRMED ? sampleJobUnlocked : sampleJobPublic;
  const hasOriginal = job.problem !== job.problem_original;

  return (
    <Screen>
      <ScreenHeader
        backTo={getHomePath(role)}
        eyebrow={`${getTradeLabel(t, job.trade)} · ${job.suburb}`}
        title={t("job.title")}
        actions={<IconLink to={generatePath(PATHS.jobChat, { jobId })} icon="chat" label={t("job.openChat")} />}
      />

      <Card tone="raised">
        <p className="lead-text" lang={isShowingOriginal ? job.problem_lang : undefined}>
          {isShowingOriginal ? job.problem_original : job.problem}
        </p>
        {hasOriginal && (
          <button type="button" className="text-toggle" onClick={() => setIsShowingOriginal(!isShowingOriginal)}>
            {isShowingOriginal ? t("translation.seeTranslation") : t("translation.seeOriginal")}
          </button>
        )}
        {job.translation_flagged && <Banner tone="info" title={t("translation.unsure")} />}
        <div className="row">
          <TradeChip trade={job.trade} tone="outline" />
          <Chip>{t(`urgency.${job.urgency}`)}</Chip>
          <Chip>{t(`size.${job.size}`)}</Chip>
          <Chip icon="mapPin">{formatDistanceKm(job.distance_km)}</Chip>
        </div>
        {job.photo_url && <Slot label="the job's photo, tap to enlarge" source={job.photo_url} minHeightPx={120} />}
      </Card>

      <JobStateRuler state={job.state} />
      <ContactCard job={job} />

      <section className="stack">
        <div className="row row--between">
          <h2 className="section-title">{t("job.quotes")}</h2>
          <IconLink to={generatePath(PATHS.jobProviders, { jobId })} icon="search" label={t("job.seeProviders")} isSmall />
        </div>
        {sampleQuotes.map((quote) => (
          <QuoteCard
            key={quote.id}
            quote={quote}
            providerName={getSampleProviderName(quote.provider_id)}
            actions={
              <Button isSmall isBlock>
                {t("job.accept")}
              </Button>
            }
          />
        ))}
      </section>

      <Slot
        label="actions for this state and role: accept or cancel (customer), confirm or decline (provider), check-in and check-out, share with a trusted contact, report"
        source="POST /api/quotes/{id}/accept · /api/jobs/{id}/confirm · /decline · /cancel"
      />
    </Screen>
  );
}
