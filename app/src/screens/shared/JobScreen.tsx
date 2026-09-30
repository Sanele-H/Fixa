// One job, seen by its customer or by a provider who quoted on it or was picked. The customer
// accepts a quote or cancels; the accepted provider confirms or declines. Contact details show
// only if the server sent them (JobUnlocked, from `confirmed` on). The job and its quotes
// refresh every few seconds, so each phone sees the other's step without reloading.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams } from "react-router";
import { getErrorMessageKey } from "../../api/errors";
import {
  useAcceptQuote,
  useCancelJob,
  useConfirmJob,
  useDeclineJob,
  useJob,
  useJobQuotes,
} from "../../api/jobs";
import { useProviderProfile } from "../../api/providers";
import { isJobUnlocked, type JobPublic, type JobState, type JobUnlocked, type Quote } from "../../api/types";
import { CHAT_WITH_PARAM, getHomePath, PATHS } from "../../app/paths";
import { getTradeLabel, TradeChip } from "../../components/Badges";
import { ContactCard } from "../../components/ContactCard";
import { CustomerDayActions, ProviderDayActions } from "../../components/JobDayActions";
import { ReportButton } from "../../components/ReportButton";
import { SafetyCard } from "../../components/SafetyCard";
import { JobStateRuler } from "../../components/JobStateRuler";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { QuoteCard } from "../../components/QuoteCard";
import { formatDistanceKm } from "../../format";
import { useCurrentUser } from "../../session/SessionContext";
import { Banner, Button, ButtonLink, Card, Chip, IconLink, Screen, ScreenHeader } from "../../ui";

type Job = JobPublic | JobUnlocked;

/** While a job is in these states, the customer can accept a quote and providers can quote. */
const OPEN_FOR_QUOTES: JobState[] = ["posted", "quoting"];
/** Once a job is in these states it's over, so it can't be cancelled. */
const FINISHED_STATES: JobState[] = ["done", "followed_up", "cancelled"];

/** The chat with one provider on this job. Customers name the provider; providers don't need to. */
function buildChatPath(jobId: string, providerId?: string) {
  const chatPath = generatePath(PATHS.jobChat, { jobId });
  return providerId ? `${chatPath}?${CHAT_WITH_PARAM}=${encodeURIComponent(providerId)}` : chatPath;
}

/**
 * The problem in the reader's language (the original a tap away), its chips and its photo.
 * A customer's distance is to their provider, so it's 0 until one is accepted and left out.
 */
function ProblemCard({ job }: { job: Job }) {
  const { t } = useTranslation();
  const [isShowingOriginal, setIsShowingOriginal] = useState(false);
  const hasOriginal = job.problem !== job.problem_original;

  return (
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
        {job.needs_licence && <Chip icon="shield">{t("job.licensedOnly")}</Chip>}
        {job.distance_km > 0 && <Chip icon="mapPin">{formatDistanceKm(job.distance_km)}</Chip>}
      </div>
      {job.photo_url && <img className="job-photo" src={job.photo_url} alt={t("job.photoAlt")} />}
    </Card>
  );
}

type CustomerQuoteProps = {
  job: Job;
  quote: Quote;
};

/** One quote as the customer sees it: who, when, how much, and what they can do with it. */
function CustomerQuote({ job, quote }: CustomerQuoteProps) {
  const { t } = useTranslation();
  const provider = useProviderProfile(quote.provider_id);
  const acceptQuote = useAcceptQuote();
  const providerName = provider.data?.display_name ?? t("role.provider");
  const canAccept = quote.state === "open" && OPEN_FOR_QUOTES.includes(job.state);

  return (
    <QuoteCard
      quote={quote}
      providerName={providerName}
      actions={
        <>
          {quote.state === "accepted" && job.state === "quote_accepted" && (
            <p className="small">{t("job.waitingForProvider", { name: providerName })}</p>
          )}
          {quote.state !== "open" && quote.state !== "accepted" && (
            <p className="small muted">{t(`job.quoteState.${quote.state}`)}</p>
          )}
          {acceptQuote.isError && <Banner tone="warning" title={t(getErrorMessageKey(acceptQuote.error))} />}
          <div className="row">
            <ButtonLink to={buildChatPath(job.id, quote.provider_id)} variant="secondary" isSmall icon="chat">
              {t("job.message")}
            </ButtonLink>
            {canAccept && (
              <Button isSmall onClick={() => acceptQuote.mutate(quote.id)} disabled={acceptQuote.isPending}>
                {t("job.accept")}
              </Button>
            )}
          </div>
        </>
      }
    />
  );
}

/** Every quote on the customer's job, with loading, error and empty states. */
function CustomerQuotes({ job }: { job: Job }) {
  const { t } = useTranslation();
  const quotes = useJobQuotes(job.id);

  if (quotes.isPending) {
    return <LoadingNote />;
  }
  if (quotes.isError) {
    return <LoadError error={quotes.error} onRetry={() => quotes.refetch()} />;
  }
  if (quotes.data.length === 0) {
    return <EmptyNote title={t("job.noQuotesTitle")}>{t("job.noQuotesBody")}</EmptyNote>;
  }
  return quotes.data.map((quote) => <CustomerQuote key={quote.id} job={job} quote={quote} />);
}

/** Confirm or decline, for the provider whose quote the customer accepted. */
function AcceptedQuoteActions({ job }: { job: Job }) {
  const { t } = useTranslation();
  const confirmJob = useConfirmJob();
  const declineJob = useDeclineJob();
  const actionError = confirmJob.error ?? declineJob.error;
  const isBusy = confirmJob.isPending || declineJob.isPending;

  return (
    <Card tone="lime">
      <p className="section-title">{t("job.acceptedTitle")}</p>
      <p className="small">{t("job.acceptedBody")}</p>
      {actionError && <Banner tone="warning" title={t(getErrorMessageKey(actionError))} />}
      <Button isBlock onClick={() => confirmJob.mutate(job.id)} disabled={isBusy}>
        {t("job.confirm")}
      </Button>
      <Button variant="secondary" isBlock onClick={() => declineJob.mutate(job.id)} disabled={isBusy}>
        {t("job.decline")}
      </Button>
    </Card>
  );
}

/** The provider's side: their own quote, confirm or decline once it's accepted, or a way to quote. */
function ProviderQuote({ job }: { job: Job }) {
  const { t } = useTranslation();
  const quotes = useJobQuotes(job.id);

  if (quotes.isPending) {
    return <LoadingNote />;
  }
  if (quotes.isError) {
    return <LoadError error={quotes.error} onRetry={() => quotes.refetch()} />;
  }
  const hasOpenQuote = quotes.data.some((quote) => quote.state === "open");
  const isAcceptedProvider = job.state === "quote_accepted" && quotes.data.some((quote) => quote.state === "accepted");
  const isPickedProvider = quotes.data.some((quote) => quote.state === "accepted") && !OPEN_FOR_QUOTES.includes(job.state);
  const isDoneJob = job.state === "done" || job.state === "followed_up";

  return (
    <>
      {isAcceptedProvider && <AcceptedQuoteActions job={job} />}
      {isPickedProvider && <ProviderDayActions job={job} />}
      {isPickedProvider && <SafetyCard jobId={job.id} state={job.state} />}
      {isDoneJob && isJobUnlocked(job) && (
        <ButtonLink
          to={`${PATHS.offAppJob}?phone=${encodeURIComponent(job.customer_phone)}&suburb=${encodeURIComponent(job.suburb)}&task=${encodeURIComponent(job.problem.slice(0, 60))}`}
          variant="lime"
          isBlock
          icon="plus"
        >
          {t("job.moreWork")}
        </ButtonLink>
      )}
      {quotes.data.map((quote) => (
        <QuoteCard key={quote.id} quote={quote} providerName={t("job.yourQuote")} />
      ))}
      {!hasOpenQuote && OPEN_FOR_QUOTES.includes(job.state) && (
        <ButtonLink to={generatePath(PATHS.jobQuote, { jobId: job.id })} isBlock icon="send">
          {t("job.sendQuote")}
        </ButtonLink>
      )}
    </>
  );
}

/** Cancelling asks once more first, since it can't be undone. */
function CancelJob({ job }: { job: Job }) {
  const { t } = useTranslation();
  const cancelJob = useCancelJob();
  const [isConfirming, setIsConfirming] = useState(false);

  if (FINISHED_STATES.includes(job.state)) {
    return null;
  }
  if (!isConfirming) {
    return (
      <Button variant="secondary" isBlock onClick={() => setIsConfirming(true)}>
        {t("job.cancel")}
      </Button>
    );
  }
  return (
    <Card>
      <p className="section-title">{t("job.cancelConfirm")}</p>
      {cancelJob.isError && <Banner tone="warning" title={t(getErrorMessageKey(cancelJob.error))} />}
      <div className="row">
        <Button onClick={() => cancelJob.mutate(job.id)} disabled={cancelJob.isPending}>
          {t("job.cancelYes")}
        </Button>
        <Button variant="secondary" onClick={() => setIsConfirming(false)}>
          {t("job.cancelNo")}
        </Button>
      </div>
    </Card>
  );
}

/** The job page once the job has loaded: the parts both people see, then each one's own. */
function JobDetails({ job }: { job: Job }) {
  const { t } = useTranslation();
  const { role } = useCurrentUser();

  return (
    <>
      <ProblemCard job={job} />
      <JobStateRuler state={job.state} />
      <ContactCard job={job} />

      <section className="stack">
        <div className="row row--between">
          <h2 className="section-title">{t("job.quotes")}</h2>
          {role === "customer" && (
            <IconLink to={generatePath(PATHS.jobProviders, { jobId: job.id })} icon="search" label={t("job.seeProviders")} isSmall />
          )}
        </div>
        {role === "customer" ? <CustomerQuotes job={job} /> : <ProviderQuote job={job} />}
      </section>

      {role === "customer" && <CustomerDayActions job={job} />}
      {role === "customer" && <SafetyCard jobId={job.id} state={job.state} />}
      {role === "customer" && <CancelJob job={job} />}
      {role === "provider" && <ReportButton targetType="job" targetId={job.id} />}
    </>
  );
}

export default function JobScreen() {
  const { t } = useTranslation();
  const { role } = useCurrentUser();
  const { jobId = "" } = useParams();
  const job = useJob(jobId);

  return (
    <Screen>
      <ScreenHeader
        backTo={getHomePath(role)}
        eyebrow={job.data && `${getTradeLabel(t, job.data.trade)} · ${job.data.suburb}`}
        title={t("job.title")}
        actions={
          role === "provider" ? <IconLink to={buildChatPath(jobId)} icon="chat" label={t("job.openChat")} /> : undefined
        }
      />
      {job.isPending && <LoadingNote />}
      {job.isError && <LoadError error={job.error} onRetry={() => job.refetch()} />}
      {job.data && <JobDetails job={job.data} />}
    </Screen>
  );
}
