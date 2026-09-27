import { useTranslation } from "react-i18next";
import type { JobPublic } from "../api/types";
import { formatDistanceKm } from "../format";
import { CardLink, Chip, Figure } from "../ui";
import { JobStateChip, TradeChip } from "./Badges";

type JobCardProps = {
  job: JobPublic;
  to: string;
  /**
   * What sits top-right: the job's state (customer's own jobs) or its distance as a big
   * figure (provider's feed, where "how far" matters most).
   */
  trailing: "state" | "distance";
};

/** One job in a list. Shows only what JobPublic carries: trade, problem, suburb, never the address. */
export function JobCard({ job, to, trailing }: JobCardProps) {
  const { t } = useTranslation();
  return (
    <CardLink to={to} tone="raised">
      <div className="row row--between">
        <TradeChip trade={job.trade} tone="outline" />
        {trailing === "state" ? (
          <JobStateChip state={job.state} />
        ) : (
          <Figure value={formatDistanceKm(job.distance_km)} size="md" />
        )}
      </div>
      <p className="section-title">{job.problem}</p>
      <div className="row">
        <Chip icon="mapPin">{job.suburb}</Chip>
        <Chip tone={job.urgency === "urgent" ? "inverse" : "default"}>{t(`urgency.${job.urgency}`)}</Chip>
        <Chip>{t(`size.${job.size}`)}</Chip>
        {job.translation_flagged && (
          <Chip tone="lavender" icon="info">
            {t("translation.unsureShort")}
          </Chip>
        )}
      </div>
    </CardLink>
  );
}
