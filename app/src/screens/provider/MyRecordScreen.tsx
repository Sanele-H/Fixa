// "My record": a provider's confirmed work, progress towards ARPL, and the exports.

import { useTranslation } from "react-i18next";
import { PATHS } from "../../app/paths";
import { EVIDENCE_KEYS } from "../../components/ProviderCard";
import { SAMPLE_EXPERIENCE_MONTHS, sampleRankedProviders, sampleRecordExport } from "../../dev/samples";
import { Button, ButtonLink, Card, Figure, IconButton, ProgressMeter, RowCard, Screen, ScreenHeader, Slot, Stat } from "../../ui";

const MONTHS_PER_YEAR = 12;
/** ARPL asks for 3 years of experience in the trade. */
const ARPL_REQUIRED_MONTHS = 3 * MONTHS_PER_YEAR;

export default function MyRecordScreen() {
  const { t } = useTranslation();
  // A provider with a long history, like the plumber in the demo.
  const evidence = sampleRankedProviders[0].evidence;
  const experienceMonths = SAMPLE_EXPERIENCE_MONTHS;
  const experienceYears = Math.floor(experienceMonths / MONTHS_PER_YEAR);
  const remainderMonths = experienceMonths % MONTHS_PER_YEAR;

  return (
    <Screen hasNav>
      <ScreenHeader
        title={t("record.title")}
        subtitle={t("record.subtitle")}
        actions={<IconButton icon="share" label={t("record.share")} />}
      />

      <Card tone="inverse">
        <p className="eyebrow">{t("record.arplProgress")}</p>
        <p className="visually-hidden">{t("record.experience", { years: experienceYears, months: remainderMonths })}</p>
        <div className="row" aria-hidden="true">
          <Figure value={experienceYears} unit={t("record.yearsUnit")} size="hero" />
          <Figure value={remainderMonths} unit={t("record.monthsUnit")} size="hero" />
        </div>
        <ProgressMeter ratio={experienceMonths / ARPL_REQUIRED_MONTHS} label={t("record.arplProgress")} />
        <p className="small muted">{t("record.arplTarget", { years: ARPL_REQUIRED_MONTHS / MONTHS_PER_YEAR })}</p>
      </Card>

      <div className="grid-2">
        {EVIDENCE_KEYS.map((key) => (
          <Card key={key} tone="raised">
            <Stat value={evidence[key]} label={t(`evidence.${key}`, { count: evidence[key] })} />
          </Card>
        ))}
      </div>

      <section className="stack">
        <Button isBlock icon="file">
          {t("record.exportArpl")}
        </Button>
        <Button variant="secondary" isBlock>
          {t("record.exportStatement")}
        </Button>
        <ButtonLink to={PATHS.offAppJob} variant="lime" isBlock icon="plus">
          {t("offApp.title")}
        </ButtonLink>
      </section>

      <RowCard eyebrow={t("record.verifyCode")} title={t("record.verifyCodeHint")} figure={sampleRecordExport.verify_code} />

      <Slot
        label="jobs grouped by trade task, before/after photos, vouches, dated timeline"
        source="contract gap: no endpoint returns the record's contents or experience months yet"
        minHeightPx={120}
      />
      <Slot label="export, then share the PDF with the Web Share API (the file where supported, else the link)" source="POST /api/record/export" />
    </Screen>
  );
}
