// The lime "Describe a job" card: the customer's main way forward, on Home, the nearby list
// and a profile opened from it. Hiring always starts here, never from a profile.

import { useTranslation } from "react-i18next";
import { PATHS } from "../app/paths";
import { CardLink, Icon } from "../ui";

/** A whole-card link to the new job screen, with a line under the title that fits the screen. */
export function DescribeJobCard({ hint }: { hint: string }) {
  const { t } = useTranslation();
  return (
    <CardLink to={PATHS.newJob} tone="lime">
      <div className="row row--between">
        <h2 className="figure figure--md">{t("home.describeJob")}</h2>
        <span className="icon-btn icon-btn--inverse" aria-hidden="true">
          <Icon name="plus" />
        </span>
      </div>
      <p>{hint}</p>
    </CardLink>
  );
}
