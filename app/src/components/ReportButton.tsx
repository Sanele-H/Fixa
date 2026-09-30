// The report button: a small "Report" link that opens a short form. Used on a job, a provider's
// profile and another person's chat message, for anything the automatic checks missed.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSendReport } from "../api/reports";
import { REPORT_REASONS, type ReportReason, type ReportTargetType } from "../api/types";
import { Banner, Button, Card, Segmented, TextArea } from "../ui";
import { ErrorBanner } from "./ErrorBanner";

const ALREADY_REPORTED_STATUS = 409;

type ReportButtonProps = {
  targetType: ReportTargetType;
  targetId: string;
};

export function ReportButton({ targetType, targetId }: ReportButtonProps) {
  const { t } = useTranslation();
  const sendReport = useSendReport();
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState<ReportReason>("scam");
  const [note, setNote] = useState("");

  if (sendReport.isSuccess) {
    return <Banner tone="info" title={t("report.thanks")} />;
  }
  if (!isOpen) {
    return (
      <button type="button" className="text-toggle" onClick={() => setIsOpen(true)}>
        {t("report.open")}
      </button>
    );
  }
  const error = sendReport.error as { status?: number } | null;
  return (
    <Card>
      <p className="section-title">{t("report.title")}</p>
      <Segmented
        label={t("report.reasonLabel")}
        options={REPORT_REASONS.map((option) => ({ value: option, label: t(`report.reason.${option}`) }))}
        value={reason}
        onChange={setReason}
      />
      <TextArea label={t("report.noteLabel")} value={note} maxLength={500} onChange={(event) => setNote(event.target.value)} />
      {sendReport.isError && (
        <ErrorBanner
          error={sendReport.error}
          overrideKey={error?.status === ALREADY_REPORTED_STATUS ? "report.alreadyReported" : undefined}
        />
      )}
      <div className="row">
        <Button
          onClick={() =>
            sendReport.mutate({ target_type: targetType, target_id: targetId, reason, note: note.trim() || undefined })
          }
          disabled={sendReport.isPending}
        >
          {t("report.send")}
        </Button>
        <Button variant="secondary" onClick={() => setIsOpen(false)}>
          {t("report.cancel")}
        </Button>
      </div>
    </Card>
  );
}
