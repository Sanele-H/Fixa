// "How this job is paid", on the job page of its customer and its picked provider: the agreed
// plan, the button to pay what's due (customer) or what's awaited (provider), a change of plan
// either side can ask for and the other must agree to, and receipts.
//
// Coming back from the checkout, the page URL has ?payment=<id> (or ?payment_cancelled=<id>).
// The payment company tells the server, not the app, so until the receipt shows up the card says
// it's waiting for confirmation.

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import {
  useAnswerPlanChange,
  useAskPlanChange,
  useJobPayment,
  usePayDue,
  type JobPayment,
  type PaymentPlan,
  type PaymentPlanChange,
} from "../api/payments";
import { PAYMENT_METHODS, type PaymentMethod } from "../api/types";
import { formatDateTime, formatRands } from "../format";
import { useCurrentUser } from "../session/SessionContext";
import { Banner, Button, Card, Segmented, TextField } from "../ui";
import { ErrorBanner } from "./ErrorBanner";
import { describeMethod, findLargestDeposit } from "./PaymentMethods";

const RETURNED_PAYMENT_PARAM = "payment";
const CANCELLED_PAYMENT_PARAM = "payment_cancelled";
const NON_DIGITS = /\D/g;

/** One sentence for a plan: "R400 in the app once the job is done." */
function usePlanSentence() {
  const { t, i18n } = useTranslation();
  return ({ method, total_rands, deposit_rands }: Pick<PaymentPlan, "method" | "total_rands" | "deposit_rands">) =>
    t(`payment.plan.${method}`, {
      total: formatRands(total_rands, i18n.language),
      deposit: formatRands(deposit_rands, i18n.language),
      rest: formatRands(total_rands - deposit_rands, i18n.language),
    });
}

/** Pay what's due (customer), or what the provider is waiting for. */
function AmountDue({ jobId, payment }: { jobId: string; payment: JobPayment }) {
  const { t, i18n } = useTranslation();
  const { role } = useCurrentUser();
  const payDue = usePayDue(jobId);
  if (!payment.due) {
    return null;
  }
  const amount = formatRands(payment.due.amount_rands, i18n.language);
  if (role !== "customer") {
    return <p className="small">{t(`payment.waitingFor.${payment.due.kind}`, { amount })}</p>;
  }
  return (
    <>
      <Button isBlock icon="lock" onClick={() => payDue.mutate()} disabled={payDue.isPending || payDue.isSuccess}>
        {t(`payment.pay.${payment.due.kind}`, { amount })}
      </Button>
      <p className="small muted">{t("payment.secureNote")}</p>
      {payDue.isError && <ErrorBanner error={payDue.error} />}
    </>
  );
}

/** A change waiting for an answer: agree or keep the plan, or take back your own. */
function PendingChange({ jobId, plan, change }: { jobId: string; plan: PaymentPlan; change: PaymentPlanChange }) {
  const { t } = useTranslation();
  const describePlan = usePlanSentence();
  const answerChange = useAnswerPlanChange(jobId);
  const planText = describePlan({ ...change, total_rands: plan.total_rands });
  const answer = (choice: "agree" | "decline") => answerChange.mutate({ changeId: change.id, answer: choice });

  return (
    <Banner tone="info" title={t(change.proposed_by_me ? "payment.changeByMe" : "payment.changeByThem", { plan: planText })}>
      {answerChange.isError && <ErrorBanner error={answerChange.error} />}
      <div className="row">
        {change.proposed_by_me ? (
          <Button variant="secondary" isSmall onClick={() => answer("decline")} disabled={answerChange.isPending}>
            {t("payment.changeWithdraw")}
          </Button>
        ) : (
          <>
            <Button isSmall onClick={() => answer("agree")} disabled={answerChange.isPending}>
              {t("payment.changeAgree")}
            </Button>
            <Button variant="secondary" isSmall onClick={() => answer("decline")} disabled={answerChange.isPending}>
              {t("payment.changeDecline")}
            </Button>
          </>
        )}
      </div>
    </Banner>
  );
}

/** "Change how we pay": pick another way (and deposit), then ask the other side. */
function AskChangeForm({ jobId, plan, onClose }: { jobId: string; plan: PaymentPlan; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const askChange = useAskPlanChange(jobId);
  const [method, setMethod] = useState<PaymentMethod>(plan.method);
  const [depositText, setDepositText] = useState(plan.deposit_rands ? String(plan.deposit_rands) : "");
  const largestDeposit = findLargestDeposit(plan.total_rands);
  const depositRands = Number(depositText);
  const isSplit = method === "in_app_split";
  const isReady = !isSplit || (depositRands >= 1 && depositRands <= largestDeposit);
  const options = PAYMENT_METHODS.map((option) => ({ value: option, label: t(`payment.method.${option}`) }));

  /** Sends the request; the card then shows it as waiting for an answer. */
  function sendChange() {
    askChange.mutate({ method, deposit_rands: isSplit ? depositRands : undefined }, { onSuccess: onClose });
  }

  return (
    <div className="stack stack--tight">
      <Segmented label={t("payment.changeButton")} options={options} value={method} onChange={setMethod} />
      {isSplit && (
        <TextField
          label={t("payment.depositLabel", { max: formatRands(largestDeposit, i18n.language) })}
          inputMode="numeric"
          value={depositText}
          onChange={(event) => setDepositText(event.target.value.replace(NON_DIGITS, ""))}
        />
      )}
      <p className="small muted">{t("payment.changeHint")}</p>
      {askChange.isError && <ErrorBanner error={askChange.error} />}
      <div className="row">
        <Button isSmall onClick={sendChange} disabled={!isReady || askChange.isPending}>
          {t("payment.changeSend")}
        </Button>
        <Button variant="secondary" isSmall onClick={onClose}>
          {t("payment.changeCancel")}
        </Button>
      </div>
    </div>
  );
}

/** Paid payments: what, how much, when, and the payment company's reference. */
function Receipts({ payment }: { payment: JobPayment }) {
  const { t, i18n } = useTranslation();
  if (payment.receipts.length === 0) {
    return null;
  }
  return (
    <section className="stack stack--tight">
      <p className="eyebrow">{t("payment.receiptsTitle")}</p>
      <ul className="stack stack--tight">
        {payment.receipts.map((receipt) => (
          <li key={receipt.id} className="row row--between small">
            <span>
              {t(`payment.receiptKind.${receipt.kind}`)} · {formatDateTime(receipt.paid_at, i18n.language)}
              <br />
              <span className="muted">
                {t(`payment.gateway.${receipt.gateway}`)} · {t("payment.receiptRef", { reference: receipt.reference })}
              </span>
              {receipt.refund_state && (
                <>
                  <br />
                  <strong>{t(`payment.refund.${receipt.refund_state}`)}</strong>
                </>
              )}
            </span>
            <strong>{formatRands(receipt.amount_rands, i18n.language)}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** What happened at the checkout we just came back from, until the receipt arrives. */
function CheckoutReturnNote({ payment }: { payment: JobPayment }) {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const returnedPaymentId = searchParams.get(RETURNED_PAYMENT_PARAM);
  if (searchParams.get(CANCELLED_PAYMENT_PARAM)) {
    return <Banner tone="info" title={t("payment.cancelled")} />;
  }
  const isConfirmed = payment.receipts.some((receipt) => receipt.id === returnedPaymentId);
  if (!returnedPaymentId || isConfirmed) {
    return null;
  }
  return <Banner tone="info" title={t("payment.confirming")} />;
}

/** The whole card, once the job has a plan (from the accepted quote on). */
export function PaymentCard({ jobId }: { jobId: string }) {
  const { t, i18n } = useTranslation();
  const payment = useJobPayment(jobId);
  const describePlan = usePlanSentence();
  const [isChanging, setIsChanging] = useState(false);
  const plan = payment.data?.plan;
  if (!payment.data || !plan) {
    return null;
  }
  const { change, can_change: canChange, paid_rands: paidRands } = payment.data;

  return (
    <Card tone="raised">
      <p className="section-title">{t("payment.planTitle")}</p>
      <p className="eyebrow">{describeMethod(t, i18n.language, plan.method, plan.deposit_rands)}</p>
      <p>{describePlan(plan)}</p>
      {paidRands > 0 && <p className="small">{t("payment.paidSoFar", { amount: formatRands(paidRands, i18n.language) })}</p>}
      <CheckoutReturnNote payment={payment.data} />
      <AmountDue jobId={jobId} payment={payment.data} />
      {change && <PendingChange jobId={jobId} plan={plan} change={change} />}
      {canChange && !change && !isChanging && (
        <Button variant="secondary" isSmall onClick={() => setIsChanging(true)}>
          {t("payment.changeButton")}
        </Button>
      )}
      {canChange && !change && isChanging && <AskChangeForm jobId={jobId} plan={plan} onClose={() => setIsChanging(false)} />}
      <Receipts payment={payment.data} />
    </Card>
  );
}
