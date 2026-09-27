// Provider quotes on a job, guided by the typical price range for this trade, size and suburb.

import { useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { PATHS } from "../../app/paths";
import { TradeChip } from "../../components/Badges";
import { sampleFeed, samplePriceRange } from "../../dev/samples";
import { formatDistanceKm, formatRands } from "../../format";
import { Banner, Button, Card, Chip, Figure, Screen, ScreenHeader, Slot, TextArea, TextField } from "../../ui";

const NON_DIGITS = /\D/g;

export default function QuoteScreen() {
  const { t, i18n } = useTranslation();
  const job = sampleFeed[0];
  // Null when there are fewer than 8 accepted quotes nearby: then show no range at all.
  const priceRange = samplePriceRange;
  const [amountText, setAmountText] = useState("");
  const amountRands = Number(amountText);
  // "Well below the range" isn't pinned down yet (P4). For now: anything under the range's low end.
  const isUnderpriced = amountText !== "" && amountRands < priceRange.low_rands;
  const priceRangeText = `${formatRands(priceRange.low_rands, i18n.language)}–${formatRands(priceRange.high_rands, i18n.language)}`;

  /** Keeps only digits, so the amount is always whole rands. */
  function updateAmount(event: ChangeEvent<HTMLInputElement>) {
    setAmountText(event.target.value.replace(NON_DIGITS, ""));
  }

  return (
    <Screen>
      <ScreenHeader backTo={PATHS.feed} title={t("quote.title")} />

      <Card tone="raised">
        <div className="row">
          <TradeChip trade={job.trade} tone="outline" />
          <Chip icon="mapPin">
            {job.suburb} · {formatDistanceKm(job.distance_km)}
          </Chip>
        </div>
        <p>{job.problem}</p>
      </Card>

      <div className="stack stack--tight">
        <label className="field__label" htmlFor="quote-amount">
          {t("quote.amountLabel")}
        </label>
        <div className="hero-input">
          <span className="figure figure--hero" aria-hidden="true">
            R
          </span>
          <input id="quote-amount" inputMode="numeric" placeholder="0" value={amountText} onChange={updateAmount} />
        </div>
      </div>

      <Card tone="lime">
        <p className="eyebrow">{t("quote.typicalRange")}</p>
        <Figure value={priceRangeText} size="md" />
        <p className="small">{t("quote.rangeBasis", { count: priceRange.n_quotes })}</p>
      </Card>

      {isUnderpriced && (
        <Banner tone="warning" title={t("quote.underpricingTitle")}>
          {t("quote.underpricingBody", { range: priceRangeText })}
        </Banner>
      )}

      <TextField label={t("quote.whenLabel")} type="datetime-local" />
      <TextArea label={t("quote.messageLabel")} rows={3} />

      <Button isBlock icon="send">
        {t("quote.send")}
      </Button>
      <Slot
        label="send the quote; if refused (prohibited_request), show its translated reason and legal route"
        source="POST /api/jobs/{job_id}/quotes · GET /api/price-range"
      />
    </Screen>
  );
}
