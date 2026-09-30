// Provider quotes on a job, guided by the typical price range for this trade, size and suburb,
// and says which ways to pay they accept.

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useNavigate, useParams } from "react-router";
import { ErrorBanner } from "../../components/ErrorBanner";
import { useCreateQuote, useJob, usePriceRange, type NewQuote } from "../../api/jobs";
import type { JobPublic, PriceRange } from "../../api/types";
import { PATHS } from "../../app/paths";
import { TradeChip } from "../../components/Badges";
import { LoadError, LoadingNote } from "../../components/LoadState";
import { isOfferedPaymentValid, PaymentMethodsField, type OfferedPayment } from "../../components/PaymentMethods";
import { formatDistanceKm, formatRands } from "../../format";
import { Banner, Button, Card, Chip, Figure, Screen, ScreenHeader, TextArea, TextField } from "../../ui";

const NON_DIGITS = /\D/g;
/**
 * A quote under this share of the range's low end is "well below" it, the same rule as
 * ranking.is_underpriced (UNDERPRICING_SHARE_OF_LOW).
 */
const UNDERPRICING_SHARE_OF_LOW = 0.8;

/** True when the amount is well below what's usually accepted nearby. */
function isUnderpriced(amountRands: number, priceRange: PriceRange | null | undefined) {
  if (!priceRange || amountRands <= 0) {
    return false;
  }
  return amountRands < UNDERPRICING_SHARE_OF_LOW * priceRange.low_rands;
}

/** The job being quoted on: trade, where, how far, and the problem in the provider's language. */
function JobSummary({ job }: { job: JobPublic }) {
  return (
    <Card tone="raised">
      <div className="row">
        <TradeChip trade={job.trade} tone="outline" />
        <Chip icon="mapPin">
          {job.suburb} · {formatDistanceKm(job.distance_km)}
        </Chip>
      </div>
      <p>{job.problem}</p>
    </Card>
  );
}

type QuoteFormProps = {
  job: JobPublic;
};

/** The price, with the typical range and an underpricing warning, then when and a note. */
function QuoteForm({ job }: QuoteFormProps) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const priceRange = usePriceRange(job.trade, job.size, job.suburb);
  const createQuote = useCreateQuote(job.id);
  const [amountText, setAmountText] = useState("");
  const [whenText, setWhenText] = useState("");
  const [message, setMessage] = useState("");
  const [offeredPayment, setOfferedPayment] = useState<OfferedPayment>({
    methods: ["in_app_after", "cash"],
    depositText: "",
  });
  const amountRands = Number(amountText);
  const offersSplit = offeredPayment.methods.includes("in_app_split");
  const range = priceRange.data;
  const rangeText = range
    ? `${formatRands(range.low_rands, i18n.language)}–${formatRands(range.high_rands, i18n.language)}`
    : "";

  /** Keeps only digits, so the amount is always whole rands. */
  function updateAmount(event: ChangeEvent<HTMLInputElement>) {
    setAmountText(event.target.value.replace(NON_DIGITS, ""));
  }

  /** Sends the quote, then opens the job page, where the provider sees it and what happens next. */
  function sendQuote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const newQuote: NewQuote = {
      amount_rands: amountRands,
      when: new Date(whenText).toISOString(),
      message: message.trim() || undefined,
      payment_methods: offeredPayment.methods,
      deposit_rands: offersSplit ? Number(offeredPayment.depositText) : undefined,
    };
    createQuote.mutate(newQuote, { onSuccess: () => navigate(generatePath(PATHS.job, { jobId: job.id })) });
  }

  return (
    <form className="stack" onSubmit={sendQuote}>
      <div className="stack stack--tight">
        <label className="field__label" htmlFor="quote-amount">
          {t("quote.amountLabel")}
        </label>
        <div className="hero-input">
          <span className="figure figure--hero" aria-hidden="true">
            R
          </span>
          <input id="quote-amount" inputMode="numeric" placeholder="0" required value={amountText} onChange={updateAmount} />
        </div>
      </div>

      {range && (
        <Card tone="lime">
          <p className="eyebrow">{t("quote.typicalRange")}</p>
          <Figure value={rangeText} size="md" />
          <p className="small">{t("quote.rangeBasis", { count: range.n_quotes })}</p>
        </Card>
      )}

      {isUnderpriced(amountRands, range) && (
        <Banner tone="warning" title={t("quote.underpricingTitle")}>
          {t("quote.underpricingBody", { range: rangeText })}
        </Banner>
      )}

      <TextField
        label={t("quote.whenLabel")}
        type="datetime-local"
        required
        value={whenText}
        onChange={(event) => setWhenText(event.target.value)}
      />
      <TextArea label={t("quote.messageLabel")} rows={3} value={message} onChange={(event) => setMessage(event.target.value)} />
      <PaymentMethodsField value={offeredPayment} totalRands={amountRands} onChange={setOfferedPayment} />

      {createQuote.isError && <ErrorBanner error={createQuote.error} />}

      <Button type="submit" isBlock icon="send" disabled={createQuote.isPending || amountRands <= 0 || !isOfferedPaymentValid(offeredPayment, amountRands)}
      >
        {t("quote.send")}
      </Button>
    </form>
  );
}

export default function QuoteScreen() {
  const { t } = useTranslation();
  const { jobId = "" } = useParams();
  const job = useJob(jobId);

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.feed} title={t("quote.title")} />
      {job.isPending && <LoadingNote />}
      {job.isError && <LoadError error={job.error} onRetry={() => job.refetch()} />}
      {job.data && (
        <>
          <JobSummary job={job.data} />
          <QuoteForm job={job.data} />
        </>
      )}
    </Screen>
  );
}
