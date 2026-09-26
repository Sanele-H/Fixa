import type { ReactNode } from "react";
import { Link } from "react-router";

/**
 * Card tones. `default` is the soft grey card, `raised` is white, `inverse` is the black
 * "selected" card, `lime` is for the main call to action, `lavender` for trust and info.
 */
export type CardTone = "default" | "raised" | "inverse" | "lime" | "lavender";

/** Builds the class list for a card of the given tone, plus any extra classes. */
function buildCardClassName(tone: CardTone, className?: string) {
  return ["card", tone !== "default" && `card--${tone}`, className].filter(Boolean).join(" ");
}

type CardProps = {
  tone?: CardTone;
  className?: string;
  children: ReactNode;
};

/** A rounded panel that groups related content. */
export function Card({ tone = "default", className, children }: CardProps) {
  return <section className={buildCardClassName(tone, className)}>{children}</section>;
}

/** A whole card that is one tap target and navigates to `to`. */
export function CardLink({ to, tone = "default", className, children }: CardProps & { to: string }) {
  return (
    <Link to={to} className={buildCardClassName(tone, className)}>
      {children}
    </Link>
  );
}

type RowCardProps = {
  /** Small line above the title, like "UTC+9" above "Tokyo". */
  eyebrow?: ReactNode;
  title: ReactNode;
  /** Big figure on the right, like "01:40" or "R450". */
  figure?: ReactNode;
  /** Small item above the figure, like a chip or icon. */
  badge?: ReactNode;
  tone?: CardTone;
  to?: string;
  onSelect?: () => void;
  isSelected?: boolean;
};

/**
 * The list row from the design: a label over a name on the left, a big figure on the right.
 * Renders a link when `to` is set, a radio-style button when `onSelect` is set, and a plain
 * card otherwise. A selected row turns black.
 */
export function RowCard({ eyebrow, title, figure, badge, tone = "default", to, onSelect, isSelected }: RowCardProps) {
  const cardTone = isSelected ? "inverse" : tone;
  const className = buildCardClassName(cardTone, "row-card");
  const content = (
    <>
      <div className="row-card__text">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <span className="row-card__title">{title}</span>
      </div>
      {(figure || badge) && (
        <div className="row-card__end">
          {badge}
          {figure && <span className="figure figure--md">{figure}</span>}
        </div>
      )}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    );
  }
  if (onSelect) {
    return (
      <button type="button" role="radio" aria-checked={Boolean(isSelected)} className={className} onClick={onSelect}>
        {content}
      </button>
    );
  }
  return <div className={className}>{content}</div>;
}
