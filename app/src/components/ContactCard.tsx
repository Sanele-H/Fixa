// The contact card on a job page. Shows phone numbers and the address only when the server
// sent them (JobUnlocked). The server decides; the app never hides details as a security measure.

import { useTranslation } from "react-i18next";
import { isJobUnlocked, type JobPublic, type JobUnlocked } from "../api/types";
import { Card, Icon } from "../ui";

/** Widths of the grey bars standing in for the hidden details. */
const REDACTED_LINE_WIDTHS = ["72%", "48%", "56%"];

/** Strips spaces so "082 000 0001" works in a tel: link. */
function buildPhoneHref(phone: string) {
  return `tel:${phone.replace(/\s/g, "")}`;
}

/** Black card: details exist but stay hidden until the provider confirms. */
function LockedContactCard() {
  const { t } = useTranslation();
  return (
    <Card tone="inverse">
      <div className="row">
        <Icon name="lock" />
        <h2 className="section-title">{t("contact.lockedTitle")}</h2>
      </div>
      <p className="small muted">{t("contact.lockedBody")}</p>
      <div className="stack stack--tight" aria-hidden="true">
        {REDACTED_LINE_WIDTHS.map((width) => (
          <div key={width} className="redacted-line" style={{ width }} />
        ))}
      </div>
    </Card>
  );
}

/** Lime card: the job is confirmed, so the address and both phone numbers are shown. */
function UnlockedContactCard({ job }: { job: JobUnlocked }) {
  const { t } = useTranslation();
  return (
    <Card tone="lime">
      <div className="row">
        <Icon name="unlock" />
        <h2 className="section-title">{t("contact.unlockedTitle")}</h2>
      </div>
      <dl className="stack stack--tight">
        <div>
          <dt className="eyebrow">{t("contact.address")}</dt>
          <dd>{job.address}</dd>
        </div>
        <div>
          <dt className="eyebrow">{t("contact.customerPhone")}</dt>
          <dd>
            <a href={buildPhoneHref(job.customer_phone)}>{job.customer_phone}</a>
          </dd>
        </div>
        <div>
          <dt className="eyebrow">{t("contact.providerPhone")}</dt>
          <dd>
            <a href={buildPhoneHref(job.provider_phone)}>{job.provider_phone}</a>
          </dd>
        </div>
      </dl>
    </Card>
  );
}

/** Picks the locked or unlocked card from what the server sent. */
export function ContactCard({ job }: { job: JobPublic | JobUnlocked }) {
  return isJobUnlocked(job) ? <UnlockedContactCard job={job} /> : <LockedContactCard />;
}
