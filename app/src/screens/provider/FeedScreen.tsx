// Provider's job feed. Each job shows only the suburb and the problem, in the provider's language.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import { PATHS } from "../../app/paths";
import { JobCard } from "../../components/JobCard";
import { sampleFeed } from "../../dev/samples";
import { IconButton, Screen, ScreenHeader, Segmented, Slot } from "../../ui";

type FeedFilter = "all" | "urgent";
const FEED_FILTERS: FeedFilter[] = ["all", "urgent"];

export default function FeedScreen() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<FeedFilter>("all");
  const visibleJobs = filter === "urgent" ? sampleFeed.filter((job) => job.urgency === "urgent") : sampleFeed;

  return (
    <Screen hasNav>
      <ScreenHeader
        title={t("feed.title")}
        subtitle={t("feed.subtitle")}
        actions={<IconButton icon="bell" label={t("home.notifications")} />}
      />

      <Segmented
        label={t("feed.filterLabel")}
        options={FEED_FILTERS.map((option) => ({ value: option, label: t(`feed.filter.${option}`) }))}
        value={filter}
        onChange={setFilter}
      />

      <div className="stack">
        {visibleJobs.map((job) => (
          <JobCard key={job.id} job={job} to={generatePath(PATHS.jobQuote, { jobId: job.id })} trailing="distance" />
        ))}
      </div>

      <Slot label="loading, empty and error states; pull to refresh" source="GET /api/feed" />
    </Screen>
  );
}
