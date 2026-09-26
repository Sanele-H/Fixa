import type { ReactNode } from "react";
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
};

/**
 * Pick one of a few options, like the 12h / 24h switch in the design.
 * Behaves as a radio group: the chosen option is black.
 */
export function Segmented<Value extends string>({ label, options, value, onChange }: SegmentedProps<Value>) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
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
