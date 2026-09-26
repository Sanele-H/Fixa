const FULL_PERCENT = 100;

/** Keeps a ratio between 0 and 1, so a bad value can never draw outside its track. */
function clampRatio(ratio: number) {
  return Math.min(Math.max(ratio, 0), 1);
}

/** Turns a 0–1 ratio into a CSS percentage string. */
function toPercent(ratio: number) {
  return `${clampRatio(ratio) * FULL_PERCENT}%`;
}

type ProgressMeterProps = {
  /** How far along, from 0 to 1. */
  ratio: number;
  /** What is being measured, read out by screen readers. Pass a translated string. */
  label: string;
};

/**
 * A lime bar filling a lighter lime track, for progress against a limit
 * (for example months of experience towards the 3 years ARPL asks for).
 * Show the numbers as text beside it; the bar is only the picture.
 */
export function ProgressMeter({ ratio, label }: ProgressMeterProps) {
  const percent = Math.round(clampRatio(ratio) * FULL_PERCENT);
  return (
    <div className="meter" role="progressbar" aria-label={label} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={FULL_PERCENT}>
      <div className="meter__fill" style={{ width: toPercent(ratio) }} />
    </div>
  );
}

type TrustRangeProps = {
  /** Trust score, 0–1, or null for a newcomer with no range yet. */
  score: number | null;
  low: number | null;
  high: number | null;
  /** The label from the API, already in the reader's language ("Strong record"). */
  label: string;
  /** Full sentence for screen readers, for example "Trust range 74 to 93 out of 100". */
  description: string;
  /** Small text under the bar on the right, for example "74–93". */
  rangeText?: string;
};

/**
 * The trust range: a band from low to high on a 0–1 track, with a dot at the score.
 * A newcomer has no range, so the whole track is hatched: "not known yet", never "zero".
 * No stars anywhere, by design.
 */
export function TrustRange({ score, low, high, label, description, rangeText }: TrustRangeProps) {
  const hasRange = low !== null && high !== null;
  return (
    <div className={hasRange ? "trust-range" : "trust-range trust-range--unknown"} role="img" aria-label={description}>
      <div className="trust-range__track">
        {hasRange && (
          <div className="trust-range__band" style={{ left: toPercent(low), width: toPercent(high - low) }} />
        )}
        {hasRange && score !== null && <div className="trust-range__marker" style={{ left: toPercent(score) }} />}
      </div>
      <div className="trust-range__caption" aria-hidden="true">
        <span>{label}</span>
        {rangeText && <span className="muted">{rangeText}</span>}
      </div>
    </div>
  );
}
