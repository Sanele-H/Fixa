import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import { useMyJobs } from "../../api/jobs";
import { PATHS } from "../../app/paths";
import { DescribeJobCard } from "../../components/DescribeJobCard";
import { JobCard } from "../../components/JobCard";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { useCurrentUser } from "../../session/SessionContext";
import { Avatar, CardLink, Icon, IconButton, Screen, ScreenHeader } from "../../ui";

/** The customer's jobs, newest first, with loading, error and empty states. */
function MyJobs() {
  const { t } = useTranslation();
  const myJobs = useMyJobs();

  if (myJobs.isPending) {
    return <LoadingNote />;
  }
  if (myJobs.isError) {
    return <LoadError error={myJobs.error} onRetry={() => myJobs.refetch()} />;
  }
  if (myJobs.data.length === 0) {
    return <EmptyNote title={t("home.noJobsTitle")}>{t("home.noJobsBody")}</EmptyNote>;
  }
  return myJobs.data.map((job) => (
    <JobCard key={job.id} job={job} to={generatePath(PATHS.job, { jobId: job.id })} trailing="state" />
  ));
}

export default function HomeScreen() {
  const { t } = useTranslation();
  const me = useCurrentUser();

  return (
    <Screen hasNav>
      <ScreenHeader
        leading={<Avatar displayName={me.display_name} />}
        actions={<IconButton icon="bell" label={t("home.notifications")} />}
        eyebrow={me.suburb}
        title={t("home.greeting", { name: me.display_name })}
      />

      <DescribeJobCard hint={t("home.describeJobHint")} />

      <CardLink to={PATHS.nearby} tone="raised">
        <div className="row row--between">
          <h2 className="section-title">{t("nearby.title")}</h2>
          <span className="icon-btn icon-btn--small" aria-hidden="true">
            <Icon name="mapPin" />
          </span>
        </div>
        <p className="muted">{t("home.nearbyHint", { suburb: me.suburb })}</p>
      </CardLink>

      <section className="stack">
        <h2 className="section-title">{t("home.yourJobs")}</h2>
        <MyJobs />
      </section>
    </Screen>
  );
}
