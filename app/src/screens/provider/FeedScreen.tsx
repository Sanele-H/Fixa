// Provider's home tab. "Your jobs" holds the jobs they quoted on or were picked for; "New jobs"
// is the feed of open jobs in their trades that they haven't quoted on yet. Each job shows only
// the suburb and the problem, in the provider's language.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import { useFeed, useMyJobs } from "../../api/jobs";
import type { JobPublic, JobState } from "../../api/types";
import { PATHS } from "../../app/paths";
import { InstallPromptCard } from "../../components/InstallPrompt";
import { JobCard } from "../../components/JobCard";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { Banner, IconButton, Screen, ScreenHeader, Segmented } from "../../ui";

type FeedFilter = "all" | "urgent";
const FEED_FILTERS: FeedFilter[] = ["all", "urgent"];

/** Jobs that are over for the provider: they drop out of "Your jobs". */
const FINISHED_STATES: JobState[] = ["done", "followed_up", "cancelled"];

/** The provider's live jobs, and the banner when a customer has accepted one of their quotes. */
function YourJobs({ jobs }: { jobs: JobPublic[] }) {
  const { t } = useTranslation();
  const liveJobs = jobs.filter((job) => !FINISHED_STATES.includes(job.state));
  if (liveJobs.length === 0) {
    return null;
  }
  const hasAcceptedQuote = liveJobs.some((job) => job.state === "quote_accepted");
  return (
    <section className="stack">
      <h2 className="section-title">{t("feed.yourJobs")}</h2>
      {hasAcceptedQuote && <Banner tone="info" title={t("feed.acceptedNote")} />}
      {liveJobs.map((job) => (
        <JobCard key={job.id} job={job} to={generatePath(PATHS.job, { jobId: job.id })} trailing="state" />
      ))}
    </section>
  );
}

type NewJobsProps = {
  /** Jobs the provider already quoted on, left out of the feed since they're in "Your jobs". */
  myJobIds: Set<string>;
  filter: FeedFilter;
};

/** The feed, minus the jobs already quoted on, with loading, error and empty states. */
function NewJobs({ myJobIds, filter }: NewJobsProps) {
  const { t } = useTranslation();
  const feed = useFeed();

  if (feed.isPending) {
    return <LoadingNote />;
  }
  if (feed.isError) {
    return <LoadError error={feed.error} onRetry={() => feed.refetch()} />;
  }
  const newJobs = feed.data.filter(
    (job) => !myJobIds.has(job.id) && (filter === "all" || job.urgency === "urgent"),
  );
  if (newJobs.length === 0) {
    return <EmptyNote title={t("feed.emptyTitle")}>{t("feed.emptyBody")}</EmptyNote>;
  }
  return newJobs.map((job) => (
    <JobCard key={job.id} job={job} to={generatePath(PATHS.jobQuote, { jobId: job.id })} trailing="distance" />
  ));
}

export default function FeedScreen() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<FeedFilter>("all");
  const myJobs = useMyJobs();
  const myJobIds = new Set((myJobs.data ?? []).map((job) => job.id));

  return (
    <Screen hasNav>
      <ScreenHeader
        title={t("feed.title")}
        subtitle={t("feed.subtitle")}
        actions={<IconButton icon="bell" label={t("home.notifications")} />}
      />

      <InstallPromptCard />

      {myJobs.isError ? (
        <LoadError error={myJobs.error} onRetry={() => myJobs.refetch()} />
      ) : (
        <YourJobs jobs={myJobs.data ?? []} />
      )}

      <section className="stack">
        <h2 className="section-title">{t("feed.newJobs")}</h2>
        <Segmented
          label={t("feed.filterLabel")}
          options={FEED_FILTERS.map((option) => ({ value: option, label: t(`feed.filter.${option}`) }))}
          value={filter}
          onChange={setFilter}
        />
        <NewJobs myJobIds={myJobIds} filter={filter} />
      </section>
    </Screen>
  );
}
