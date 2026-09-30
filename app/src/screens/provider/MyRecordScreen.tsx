// "My record": a provider's confirmed work, progress towards ARPL, and the exports. Exporting
// makes a PDF with a verify code anyone can check, and opens the public record page: its link
// is only offered after an export, since exporting is the provider's sign they want it shared.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getErrorCode, getErrorMessageKey } from "../../api/errors";
import { useProviderProfile } from "../../api/providers";
import { readRecordPdf, useExportRecord, useRecordSummary } from "../../api/record";
import type { RecordExport, RecordMode, RecordSummary } from "../../api/types";
import { PATHS } from "../../app/paths";
import { getTradeLabel } from "../../components/Badges";
import { LoadError, LoadingNote } from "../../components/LoadState";
import { EVIDENCE_KEYS } from "../../components/ProviderCard";
import { useCurrentUser } from "../../session/SessionContext";
import { shareFile, shareLink, type ShareOutcome } from "../../share";
import { Banner, Button, ButtonLink, Card, Figure, ProgressMeter, RowCard, Screen, ScreenHeader, Stat } from "../../ui";

const MONTHS_PER_YEAR = 12;
const LAST_OFF_APP_JOB_DATE_KEY = "fixa.lastOffAppJobDate";
const NUDGE_THRESHOLD_DAYS = 30;
const MS_PER_DAY = 86_400_000;

/** True when the provider hasn't logged an off-app job in the last 30 days. */
function shouldShowNudge(): boolean {
  try {
    const stored = localStorage.getItem(LAST_OFF_APP_JOB_DATE_KEY);
    if (!stored) return true;
    const elapsed = Date.now() - new Date(stored).getTime();
    return elapsed >= NUDGE_THRESHOLD_DAYS * MS_PER_DAY;
  } catch {
    return false;
  }
}
/** ARPL asks for 3 years of experience in the trade (18 months or 4 years for a few categories). */
const ARPL_REQUIRED_MONTHS = 3 * MONTHS_PER_YEAR;
const PDF_TYPE = "application/pdf";

/** The line shown after sharing, when there was no share sheet (or nothing to say). */
const SHARE_OUTCOME_KEYS: Partial<Record<ShareOutcome, string>> = {
  downloaded: "record.pdfDownloaded",
  copied: "record.linkCopied",
};

/** Messages for the reasons the server gives when it refuses an export. */
const EXPORT_ERROR_KEYS: Record<string, string> = {
  no_jobs: "record.noJobs",
  no_arpl_trade: "record.noArplTrade",
};

/** Why an export failed: no confirmed jobs, no ARPL trade, or the usual reasons. */
function getExportErrorKey(error: unknown) {
  return EXPORT_ERROR_KEYS[getErrorCode(error) ?? ""] ?? getErrorMessageKey(error);
}

/** Years and months of experience as big figures, and how far that is towards ARPL. */
function ArplProgress({ summary }: { summary: RecordSummary }) {
  const { t } = useTranslation();
  const years = Math.floor(summary.experience_months / MONTHS_PER_YEAR);
  const months = summary.experience_months % MONTHS_PER_YEAR;
  return (
    <Card tone="inverse">
      <p className="eyebrow">
        {t("record.arplProgress")}
        {summary.arpl_trade && ` · ${getTradeLabel(t, summary.arpl_trade)}`}
      </p>
      <p className="visually-hidden">{t("record.experience", { years, months })}</p>
      <div className="row" aria-hidden="true">
        <Figure value={years} unit={t("record.yearsUnit")} size="hero" />
        <Figure value={months} unit={t("record.monthsUnit")} size="hero" />
      </div>
      {summary.arpl_trade ? (
        <>
          <ProgressMeter ratio={Math.min(1, summary.experience_months / ARPL_REQUIRED_MONTHS)} label={t("record.arplProgress")} />
          <p className="small muted">{t("record.arplTarget", { years: ARPL_REQUIRED_MONTHS / MONTHS_PER_YEAR })}</p>
        </>
      ) : (
        <p className="small muted">{t("record.noArplTrade")}</p>
      )}
    </Card>
  );
}

/** The four evidence counts, from the provider's own profile. */
function EvidenceTiles({ providerId }: { providerId: string }) {
  const { t } = useTranslation();
  const profile = useProviderProfile(providerId);
  if (profile.isPending) {
    return <LoadingNote />;
  }
  if (profile.isError) {
    return <LoadError error={profile.error} onRetry={() => profile.refetch()} />;
  }
  const { evidence } = profile.data;
  return (
    <div className="grid-2">
      {EVIDENCE_KEYS.map((key) => (
        <Card key={key} tone="raised">
          <Stat value={evidence[key]} label={t(`evidence.${key}`, { count: evidence[key] })} />
        </Card>
      ))}
    </div>
  );
}

/** Downloads the export's PDF and hands it to the share sheet, named by its verify code. */
async function shareRecordPdf(recordExport: RecordExport, title: string) {
  const pdf = await readRecordPdf(recordExport);
  const file = new File([pdf], `fixa-record-${recordExport.verify_code}.pdf`, { type: PDF_TYPE });
  return shareFile(file, title);
}

/** The two exports, then the verify code and the record link once there's an export. */
function RecordExports({ providerId }: { providerId: string }) {
  const { t } = useTranslation();
  const exportRecord = useExportRecord();
  const [shareOutcome, setShareOutcome] = useState<ShareOutcome | null>(null);
  const [shareError, setShareError] = useState<unknown>(null);
  const outcomeKey = shareOutcome ? SHARE_OUTCOME_KEYS[shareOutcome] : undefined;

  /** Makes the PDF, then shares or downloads it. A failed download shows why. */
  async function exportAndShare(mode: RecordMode) {
    setShareOutcome(null);
    setShareError(null);
    try {
      const recordExport = await exportRecord.mutateAsync(mode);
      setShareOutcome(await shareRecordPdf(recordExport, t("record.title")));
    } catch (error) {
      setShareError(error);
    }
  }

  /** Shares the public record page, which exists now that there's an export. */
  async function shareRecordLink() {
    const recordUrl = `${window.location.origin}/record/${encodeURIComponent(providerId)}`;
    setShareOutcome(await shareLink(recordUrl, t("record.title")));
  }

  return (
    <section className="stack">
      <Button isBlock icon="file" onClick={() => exportAndShare("arpl")} disabled={exportRecord.isPending}>
        {t("record.exportArpl")}
      </Button>
      <Button variant="secondary" isBlock onClick={() => exportAndShare("statement")} disabled={exportRecord.isPending}>
        {t("record.exportStatement")}
      </Button>
      {exportRecord.isPending && <LoadingNote />}
      {shareError !== null && <Banner tone="warning" title={t(getExportErrorKey(shareError))} />}
      {exportRecord.data && (
        <>
          <RowCard eyebrow={t("record.verifyCode")} title={t("record.verifyCodeHint")} figure={exportRecord.data.verify_code} />
          <Button variant="secondary" isBlock icon="share" onClick={shareRecordLink}>
            {t("record.share")}
          </Button>
        </>
      )}
      {outcomeKey && <p className="small muted" role="status">{t(outcomeKey)}</p>}
    </section>
  );
}

export default function MyRecordScreen() {
  const { t } = useTranslation();
  const me = useCurrentUser();
  const summary = useRecordSummary();

  return (
    <Screen hasNav>
      <ScreenHeader title={t("record.title")} subtitle={t("record.subtitle")} />

      {summary.isPending && <LoadingNote />}
      {summary.isError && <LoadError error={summary.error} onRetry={() => summary.refetch()} />}
      {summary.data && <ArplProgress summary={summary.data} />}

      <EvidenceTiles providerId={me.id} />

      <RecordExports providerId={me.id} />

      {shouldShowNudge() && (
        <Banner tone="info" title={t("record.nudgeTitle")}>
          <p className="small">{t("record.nudgeBody")}</p>
        </Banner>
      )}

      <ButtonLink to={PATHS.offAppJob} variant="lime" isBlock icon="plus">
        {t("offApp.title")}
      </ButtonLink>
    </Screen>
  );
}
