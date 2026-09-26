import type { ReactNode } from "react";

export type FigureSize = "md" | "lg" | "hero";

type FigureProps = {
  value: ReactNode;
  unit?: ReactNode;
  /** md for list rows, lg for cards, hero for the one clock-face number a screen leads with. */
  size?: FigureSize;
};

/**
 * A big number in the design's clock-face style, like "08 40" or "R450".
 * Use `hero` at most once per screen.
 */
export function Figure({ value, unit, size = "lg" }: FigureProps) {
  const className = size === "lg" ? "figure" : `figure figure--${size}`;
  return (
    <span className={className}>
      {value}
      {unit && <span className="figure__unit">{unit}</span>}
    </span>
  );
}

type StatProps = FigureProps & {
  label: ReactNode;
};

/** A number with a label under it, for stat tiles like "9 jobs" or "62 bpm". */
export function Stat({ label, ...figureProps }: StatProps) {
  return (
    <div className="stat">
      <Figure {...figureProps} />
      <span className="stat__label">{label}</span>
    </div>
  );
}

type AvatarProps = {
  displayName: string;
  isLarge?: boolean;
};

/**
 * A round badge with the person's first initial.
 * Providers' real photos only arrive once a job is confirmed (JobUnlocked.provider_photo_url),
 * so the initial is what most screens show.
 */
export function Avatar({ displayName, isLarge }: AvatarProps) {
  return (
    <span className={isLarge ? "avatar avatar--lg" : "avatar"} aria-hidden="true">
      {displayName.charAt(0).toUpperCase()}
    </span>
  );
}
