import { useEffect, useRef, type ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export type ChipTone = "default" | "lime" | "lavender" | "inverse" | "outline" | "warning";

type ChipProps = {
  tone?: ChipTone;
  icon?: IconName;
  children: ReactNode;
};

/** A small rounded label: a trade, a state, a badge. Not a button. */
export function Chip({ tone = "default", icon, children }: ChipProps) {
  const className = tone === "default" ? "chip" : `chip chip--${tone}`;
  return (
    <span className={className}>
      {icon && <Icon name={icon} sizePx={16} />}
      {children}
    </span>
  );
}

export type SegmentedOption<Value extends string> = {
  value: Value;
  label: ReactNode;
};

type SegmentedProps<Value extends string> = {
  /** Read out by screen readers as the group's name. Pass a translated string. */
  label: string;
  options: SegmentedOption<Value>[];
  value: Value;
  onChange: (value: Value) => void;
  /**
   * For long lists (the 13 trades): each option keeps its own width and the row scrolls
   * sideways, instead of every option squeezing into an equal share of the width.
   */
  isScrollable?: boolean;
};

/**
 * Pick one of a few options, like the 12h / 24h switch in the design.
 * Behaves as a radio group: the chosen option is black. A scrollable one brings the chosen
 * option into view, so a suggested trade far along the row isn't hidden off the edge.
 */
export function Segmented<Value extends string>({ label, options, value, onChange, isScrollable }: SegmentedProps<Value>) {
  const groupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isScrollable) {
      return;
    }
    const group = groupRef.current;
    const chosenOption = group?.querySelector<HTMLElement>('[aria-checked="true"]');
    if (!group || !chosenOption) {
      return;
    }
    // Only the row scrolls, never the page: centre the chosen option within the row.
    const left = chosenOption.offsetLeft - (group.clientWidth - chosenOption.offsetWidth) / 2;
    group.scrollTo({ left, behavior: "smooth" });
  }, [isScrollable, value]);

  return (
    <div ref={groupRef} className={isScrollable ? "segmented segmented--scroll" : "segmented"} role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={option.value === value}
          className="segmented__option"
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
