// Customer describes the problem in their own words. The app suggests a trade, urgency and
// size from that description, and the customer confirms or changes them.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath } from "react-router";
import { JOB_SIZES, URGENCIES, type JobSize, type Urgency } from "../../api/types";
import { PATHS } from "../../app/paths";
import { TradeChip } from "../../components/Badges";
import { sampleJobIntent, sampleJobPublic } from "../../dev/samples";
import { ButtonLink, Card, Icon, Screen, ScreenHeader, Segmented, Slot, TextArea } from "../../ui";

export default function NewJobScreen() {
  const { t } = useTranslation();
  const jobIntent = sampleJobIntent;
  const [urgency, setUrgency] = useState<Urgency>(jobIntent.urgency);
  const [size, setSize] = useState<JobSize>(jobIntent.size);

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.home} title={t("newJob.title")} subtitle={t("newJob.subtitle")} />

      <TextArea label={t("newJob.describeLabel")} placeholder={t("newJob.describeExample")} />
      <Slot label="send the description, show a short wait, then fill the card below" source="POST /api/jobs/understand" />

      <Card tone="inverse">
        <p className="eyebrow">{t("newJob.suggested")}</p>
        <div className="row">
          <TradeChip trade={jobIntent.trade} tone="lime" />
        </div>
        <Slot label="change the trade (the 11 trades in data/glossary.json)" />
        <p className="eyebrow">{t("newJob.urgency")}</p>
        <Segmented
          label={t("newJob.urgency")}
          options={URGENCIES.map((option) => ({ value: option, label: t(`urgency.${option}`) }))}
          value={urgency}
          onChange={setUrgency}
        />
        <p className="eyebrow">{t("newJob.size")}</p>
        <Segmented
          label={t("newJob.size")}
          options={JOB_SIZES.map((option) => ({ value: option, label: t(`size.${option}`) }))}
          value={size}
          onChange={setSize}
        />
      </Card>

      <button type="button" className="photo-tile">
        <Icon name="camera" sizePx={28} />
        <span>{t("newJob.addPhoto")}</span>
        <span className="muted">{t("newJob.photoHint")}</span>
      </button>
      <Slot label="shrink the photo on the phone (longest side ~1280 px, JPEG ~0.7), then upload" source="POST /api/photos" />

      <ButtonLink to={generatePath(PATHS.jobProviders, { jobId: sampleJobPublic.id })} isBlock>
        {t("newJob.post")}
      </ButtonLink>
      <Slot
        label="post the job; if refused (prohibited_request), show its translated reason and legal route in a critical Banner"
        source="POST /api/jobs"
      />
    </Screen>
  );
}
