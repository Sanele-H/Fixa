import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { Quote } from "../api/types";
import { formatDateTime, formatRands } from "../format";
import { Card, Figure } from "../ui";
import { OfferedMethods } from "./PaymentMethods";

type QuoteCardProps = {
  quote: Quote;
  providerName: string;
  /** Buttons for this quote, for example Accept. Left to the screen, since they depend on who's looking. */
  actions?: ReactNode;
};

/** A quote: who, when they can come, the price as a big figure, and the ways to pay it. */
export function QuoteCard({ quote, providerName, actions }: QuoteCardProps) {
  const { i18n } = useTranslation();
  return (
    <Card tone="raised">
      <div className="row-card">
        <div className="row-card__text">
          <span className="eyebrow">{providerName}</span>
          <span className="row-card__title">{formatDateTime(quote.when, i18n.language)}</span>
        </div>
        <Figure value={formatRands(quote.amount_rands, i18n.language)} size="md" />
      </div>
      {quote.message && <p className="small muted">{quote.message}</p>}
      <OfferedMethods quote={quote} />
      {actions}
    </Card>
  );
}
