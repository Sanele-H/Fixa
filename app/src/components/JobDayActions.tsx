// What happens on the day, for each person: the provider checks in and says the work is finished,
// the customer says whether it was done or nobody turned up. Afterwards the customer can vouch,
// and is told we will ask in two weeks whether the fix is holding.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useCheckIn, useCheckOut, useFinishJob } from "../api/lifecycle";
import { useJobQuotes } from "../api/jobs";
import { useProviderProfile } from "../api/providers";
import type { JobPublic, JobUnlocked } from "../api/types";
import { getCameraPath } from "../app/paths";
import { formatDateTime } from "../format";
import { shareText, type ShareOutcome } from "../share";
import { Banner, Button, ButtonLink, Card } from "../ui";
import { ErrorBanner } from "./ErrorBanner";
import { VouchForm } from "./VouchForm";

type Job = JobPublic | JobUnlocked;

type ShareTrustedButtonProps = {
  job: Job;
  providerName: string;
  /** When the provider said they'd come (the accepted quote's time), if we know it. */
  arrivalTime?: string;
};

/**
 * Lets the customer send who is coming, to which suburb and when, to someone they trust.
 * It sends text only, no link: the job page needs the customer's login, and the provider's
 * public record page only exists once the provider chooses to share it. With no arrival time
 * the message leaves the time out rather than guess one.
 */
function ShareTrustedButton({ job, providerName, arrivalTime }: ShareTrustedButtonProps) {
  const { t, i18n } = useTranslation();
  const [shareOutcome, setShareOutcome] = useState<ShareOutcome | null>(null);

  /** Builds the message and hands it to the share sheet, or copies it. */
  async function shareJobDetails() {
    const details = { name: providerName, suburb: job.suburb };
    const text = arrivalTime
      ? t("share.text", { ...details, time: formatDateTime(arrivalTime, i18n.language) })
      : t("share.textNoTime", details);
    try {
      setShareOutcome(await shareText(text, t("share.title", { name: providerName })));
    } catch {
      // No share sheet and the clipboard is blocked: there's nothing more the button can do.
      setShareOutcome(null);
    }
  }

  return (
    <>
      <Button variant="secondary" isBlock icon="share" onClick={shareJobDetails}>
        {t("share.trusted")}
      </Button>
      {shareOutcome === "copied" && <Banner tone="info" title={t("share.copied")} />}
    </>
  );
}

/** Opens the camera for a before or after photo, stamped with this job's suburb. */
function TakePhotoLink({ job }: { job: Job }) {
  const { t } = useTranslation();
  return (
    <ButtonLink to={getCameraPath(job.id, job.suburb)} variant="secondary" isBlock icon="camera">
      {t("camera.title")}
    </ButtonLink>
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
        <TakePhotoLink job={job} />
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
        <TakePhotoLink job={job} />
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
        <ShareTrustedButton job={job} providerName={providerName} arrivalTime={acceptedQuote?.when} />
      </div>
    );
  }
  if ((job.state === "done" || job.state === "followed_up") && pickedProviderId) {
    return (
      <>
        {job.state === "done" && <Banner tone="info" title={t("lifecycle.followUpSoon")} />}
        <ShareTrustedButton job={job} providerName={providerName} arrivalTime={acceptedQuote?.when} />
        <VouchForm providerId={pickedProviderId} providerName={providerName} />
      </>
    );
  }
  return null;
}
