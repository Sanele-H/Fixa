// What happens on the day, for each person: the provider checks in and says the work is finished,
// the customer says whether it was done or nobody turned up. Afterwards the customer can vouch,
// and is told we will ask in two weeks whether the fix is holding.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCheckIn, useCheckOut, useFinishJob } from "../api/lifecycle";
import { useJobQuotes } from "../api/jobs";
import { useProviderProfile } from "../api/providers";
import type { JobPublic, JobUnlocked } from "../api/types";
import { formatDate, formatDateTime } from "../format";
import { Banner, Button, Card } from "../ui";
import { ErrorBanner } from "./ErrorBanner";
import { VouchForm } from "./VouchForm";

type Job = JobPublic | JobUnlocked;

/** Button allowing the customer to share details of a confirmed job with someone they trust. */
function ShareTrustedButton({ job, providerName, quoteWhen }: { job: Job; providerName: string; quoteWhen?: string }) {
  const { t, i18n } = useTranslation();
  const [copied, setCopied] = useState(false);

  const formattedTime = quoteWhen ? formatDateTime(quoteWhen, i18n.language) : formatDate(job.created_at, i18n.language);

  const handleShare = async () => {
    const text = t("share.text", {
      name: providerName,
      suburb: job.suburb,
      time: formattedTime,
    });
    const title = t("share.title", { name: providerName });
    const url = window.location.href;

    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, text, url });
      } catch {
        // User cancelled share
      }
    } else if (typeof navigator !== "undefined" && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(`${text}\n${url}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
      } catch {
        // Clipboard error
      }
    }
  };

  return (
    <Button variant="secondary" isBlock icon="share" onClick={handleShare}>
      {copied ? t("share.copied") : t("share.trusted")}
    </Button>
  );
}

/** The provider's side, only for the provider who was picked for this job. */
export function ProviderDayActions({ job }: { job: Job }) {
  const { t } = useTranslation();
  const checkIn = useCheckIn();
  const checkOut = useCheckOut();

  if (job.state === "confirmed") {
    return (
      <Card tone="lime">
        <p className="section-title">{t("lifecycle.arrivedTitle")}</p>
        <p className="small">{t("lifecycle.arrivedBody")}</p>
        {checkIn.isError && <ErrorBanner error={checkIn.error} />}
        <Button isBlock onClick={() => checkIn.mutate(job.id)} disabled={checkIn.isPending}>
          {t("lifecycle.checkIn")}
        </Button>
      </Card>
    );
  }
  if (job.state === "in_progress") {
    return (
      <Card tone="lime">
        <p className="section-title">{t("lifecycle.finishedTitle")}</p>
        <p className="small">{t("lifecycle.finishedBody")}</p>
        {checkOut.isError && <ErrorBanner error={checkOut.error} />}
        {checkOut.isSuccess ? (
          <Banner tone="info" title={t("lifecycle.waitingForCustomer")} />
        ) : (
          <Button isBlock onClick={() => checkOut.mutate(job.id)} disabled={checkOut.isPending}>
            {t("lifecycle.checkOut")}
          </Button>
        )}
      </Card>
    );
  }
  return null;
}

/** The customer's side: done, or nobody came (which asks once more); then thanks, share and a vouch. */
export function CustomerDayActions({ job }: { job: Job }) {
  const { t } = useTranslation();
  const finishJob = useFinishJob();
  const quotes = useJobQuotes(job.id);
  const [isConfirmingNoShow, setIsConfirmingNoShow] = useState(false);
  const acceptedQuote = quotes.data?.find((quote) => quote.state === "accepted");
  const pickedProviderId = acceptedQuote?.provider_id ?? "";
  const pickedProvider = useProviderProfile(pickedProviderId || undefined);
  const providerName = pickedProvider.data?.display_name ?? t("role.provider");

  if (job.state === "confirmed" || job.state === "in_progress") {
    return (
      <div className="stack">
        <Card tone="lime">
          <p className="section-title">{t("lifecycle.isItDoneTitle")}</p>
          <p className="small">{t("lifecycle.isItDoneBody", { name: providerName })}</p>
          {finishJob.isError && <ErrorBanner error={finishJob.error} />}
          <Button isBlock onClick={() => finishJob.mutate({ jobId: job.id, completed: true })} disabled={finishJob.isPending}>
            {t("lifecycle.itIsDone")}
          </Button>
          {isConfirmingNoShow ? (
            <Card>
              <p className="section-title">{t("lifecycle.noShowConfirm", { name: providerName })}</p>
              <div className="row">
                <Button onClick={() => finishJob.mutate({ jobId: job.id, completed: false })} disabled={finishJob.isPending}>
                  {t("lifecycle.noShowYes")}
                </Button>
                <Button variant="secondary" onClick={() => setIsConfirmingNoShow(false)}>
                  {t("lifecycle.noShowNo")}
                </Button>
              </div>
            </Card>
          ) : (
            <Button variant="secondary" isBlock onClick={() => setIsConfirmingNoShow(true)}>
              {t("lifecycle.noShow")}
            </Button>
          )}
        </Card>
        <ShareTrustedButton job={job} providerName={providerName} quoteWhen={acceptedQuote?.when} />
      </div>
    );
  }
  if ((job.state === "done" || job.state === "followed_up") && pickedProviderId) {
    return (
      <>
        {job.state === "done" && <Banner tone="info" title={t("lifecycle.followUpSoon")} />}
        <ShareTrustedButton job={job} providerName={providerName} quoteWhen={acceptedQuote?.when} />
        <VouchForm providerId={pickedProviderId} providerName={providerName} />
      </>
    );
  }
  return null;
}
