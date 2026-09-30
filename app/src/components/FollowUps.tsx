// "Is the fix still working?": the customer's jobs that finished two weeks ago or more. The answer
// is one of the signals behind the provider's trust range, so it is asked once per job.

import { useTranslation } from "react-i18next";
import { useAnswerStillWorking, useFollowUps } from "../api/lifecycle";
import type { JobPublic, JobUnlocked } from "../api/types";
import { Button, Card } from "../ui";
import { ErrorBanner } from "./ErrorBanner";

function FollowUp({ job }: { job: JobPublic | JobUnlocked }) {
  const { t } = useTranslation();
  const answer = useAnswerStillWorking();

  return (
    <Card tone="lime">
      <p className="section-title">{t("followUp.title")}</p>
      <p>{job.problem}</p>
      {answer.isError && <ErrorBanner error={answer.error} />}
      <div className="row">
        <Button isSmall onClick={() => answer.mutate({ jobId: job.id, stillWorking: true })} disabled={answer.isPending}>
          {t("followUp.yes")}
        </Button>
        <Button
          variant="secondary"
          isSmall
          onClick={() => answer.mutate({ jobId: job.id, stillWorking: false })}
          disabled={answer.isPending}
        >
          {t("followUp.no")}
        </Button>
      </div>
    </Card>
  );
}

/** Nothing at all when no job is due. */
export function FollowUps() {
  const followUps = useFollowUps();
  if (!followUps.data || followUps.data.length === 0) {
    return null;
  }
  return (
    <section className="stack">
      {followUps.data.map((job) => (
        <FollowUp key={job.id} job={job} />
      ))}
    </section>
  );
}
