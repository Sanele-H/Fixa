// Provider logs a job done outside the app. The customer confirms by replying to an SMS in
// their language, and only then does it count towards the provider's record.

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { getErrorCode, getErrorMessageKey } from "../../api/errors";
import { useLogOffAppJob, type NewOffAppJob } from "../../api/record";
import type { OffAppJob } from "../../api/types";
import { PATHS } from "../../app/paths";
import { formatDate, formatRands } from "../../format";
import { useCurrentUser } from "../../session/SessionContext";
import { Banner, Button, Card, Screen, ScreenHeader, TextField } from "../../ui";

const NON_DIGITS = /\D/g;
/** The server's limit for "What did you do?" (NewOffAppJob.trade_task). */
const TRADE_TASK_MAX_CHARS = 60;
const MS_PER_MINUTE = 60_000;

/** The reasons the server gives when it refuses an off-app job, each with its own message. */
const OFF_APP_ERROR_CODES = [
  "self_confirmation",
  "invalid_phone",
  "invalid_date",
  "duplicate",
  "monthly_cap",
  "customer_busy",
  "sms_failed",
];

/** Why logging failed: the server's reason when it gave one we know, else the usual message. */
function getOffAppErrorKey(error: unknown) {
  const code = getErrorCode(error);
  return code && OFF_APP_ERROR_CODES.includes(code) ? `offApp.error.${code}` : getErrorMessageKey(error);
}

/** Today as YYYY-MM-DD in the phone's own time zone, the latest date a past job can have. */
function getTodayDate() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * MS_PER_MINUTE).toISOString().slice(0, 10);
}

type OffAppFormProps = {
  onLogged: (job: OffAppJob) => void;
};

/** The customer's number, what was done, when and where, and optionally what it cost. */
function OffAppForm({ onLogged }: OffAppFormProps) {
  const { t } = useTranslation();
  const me = useCurrentUser();
  const logOffAppJob = useLogOffAppJob();
  const [customerPhone, setCustomerPhone] = useState("");
  const [tradeTask, setTradeTask] = useState("");
  const [date, setDate] = useState("");
  const [suburb, setSuburb] = useState(me.suburb);
  const [amountText, setAmountText] = useState("");

  /** Keeps only digits, so the amount is always whole rands. */
  function updateAmount(event: ChangeEvent<HTMLInputElement>) {
    setAmountText(event.target.value.replace(NON_DIGITS, ""));
  }

  /** Sends the job; the server texts the customer to confirm it. */
  function logJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const newOffAppJob: NewOffAppJob = {
      customer_phone: customerPhone,
      trade_task: tradeTask.trim(),
      date,
      suburb: suburb.trim(),
      amount_rands: amountText ? Number(amountText) : undefined,
    };
    logOffAppJob.mutate(newOffAppJob, { onSuccess: onLogged });
  }

  return (
    <form className="stack" onSubmit={logJob}>
      <Card tone="raised">
        <TextField
          label={t("offApp.customerPhone")}
          type="tel"
          inputMode="tel"
          placeholder="082 000 0001"
          required
          value={customerPhone}
          onChange={(event) => setCustomerPhone(event.target.value)}
        />
        <TextField
          label={t("offApp.tradeTask")}
          placeholder={t("offApp.tradeTaskExample")}
          required
          maxLength={TRADE_TASK_MAX_CHARS}
          value={tradeTask}
          onChange={(event) => setTradeTask(event.target.value)}
        />
        <TextField
          label={t("offApp.date")}
          type="date"
          required
          max={getTodayDate()}
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
        <TextField label={t("offApp.suburb")} required value={suburb} onChange={(event) => setSuburb(event.target.value)} />
        <TextField
          label={t("offApp.amount")}
          hint={t("offApp.amountHint")}
          inputMode="numeric"
          value={amountText}
          onChange={updateAmount}
        />
      </Card>

      <Banner tone="info" title={t("offApp.smsNoteTitle")}>
        {t("offApp.smsNoteBody")}
      </Banner>

      {logOffAppJob.isError && <Banner tone="warning" title={t(getOffAppErrorKey(logOffAppJob.error))} />}

      <Button type="submit" isBlock icon="send" disabled={logOffAppJob.isPending}>
        {t("offApp.submit")}
      </Button>
    </form>
  );
}

type LoggedJobProps = {
  job: OffAppJob;
  onLogAnother: () => void;
};

/** What was sent, and that it counts once the customer replies YES. */
function LoggedJob({ job, onLogAnother }: LoggedJobProps) {
  const { t, i18n } = useTranslation();
  const details = [job.suburb, formatDate(job.date, i18n.language)];
  if (job.amount_rands !== null) {
    details.push(formatRands(job.amount_rands, i18n.language));
  }
  return (
    <>
      <Card tone="lime">
        <p className="eyebrow">{t("offApp.sentTitle")}</p>
        <p className="section-title">{job.trade_task}</p>
        <p className="small">{details.join(" · ")}</p>
        <p className="small">{t("offApp.sentBody")}</p>
      </Card>
      <Button variant="secondary" isBlock onClick={onLogAnother}>
        {t("offApp.logAnother")}
      </Button>
    </>
  );
}

export default function OffAppJobScreen() {
  const { t } = useTranslation();
  const [loggedJob, setLoggedJob] = useState<OffAppJob | null>(null);

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.myRecord} title={t("offApp.title")} subtitle={t("offApp.subtitle")} />
      {loggedJob ? (
        <LoggedJob job={loggedJob} onLogAnother={() => setLoggedJob(null)} />
      ) : (
        <OffAppForm onLogged={setLoggedJob} />
      )}
    </Screen>
  );
}
