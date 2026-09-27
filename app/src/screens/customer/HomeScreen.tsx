import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import { PATHS } from "../../app/paths";
import { JobCard } from "../../components/JobCard";
import { sampleJobPublic, sampleMe } from "../../dev/samples";
import { Avatar, CardLink, Icon, IconButton, Screen, ScreenHeader, Slot } from "../../ui";

export default function HomeScreen() {
  const { t } = useTranslation();
  const me = sampleMe;

  return (
    <Screen hasNav>
      <ScreenHeader
        leading={<Avatar displayName={me.display_name} />}
        actions={<IconButton icon="bell" label={t("home.notifications")} />}
        eyebrow={me.suburb}
        title={t("home.greeting", { name: me.display_name })}
      />

      <CardLink to={PATHS.newJob} tone="lime">
        <div className="row row--between">
          <h2 className="figure figure--md">{t("home.describeJob")}</h2>
          <span className="icon-btn icon-btn--inverse" aria-hidden="true">
            <Icon name="plus" />
          </span>
        </div>
        <p>{t("home.describeJobHint")}</p>
      </CardLink>

      <section className="stack">
        <h2 className="section-title">{t("home.yourJobs")}</h2>
        <JobCard job={sampleJobPublic} to={generatePath(PATHS.job, { jobId: sampleJobPublic.id })} trailing="state" />
        <Slot label="the customer's jobs, newest first, plus an empty state" source="contract gap: no endpoint lists a customer's jobs yet" />
      </section>
    </Screen>
  );
}
