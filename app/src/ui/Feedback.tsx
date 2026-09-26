import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

export type BannerTone = "info" | "warning" | "critical";

const BANNER_ICONS: Record<BannerTone, IconName> = {
  info: "info",
  warning: "alert",
  critical: "ban",
};

type BannerProps = {
  tone: BannerTone;
  title: ReactNode;
  children?: ReactNode;
};

/**
 * A short message inside a screen.
 * info: "This may not have translated well". warning: "You may be underpricing".
 * critical: a refused request, with the legal route in `children`.
 * Every tone has its own icon, so the meaning never rests on colour alone.
 */
export function Banner({ tone, title, children }: BannerProps) {
  return (
    <div className={`banner banner--${tone}`} role={tone === "critical" ? "alert" : "status"}>
      <Icon name={BANNER_ICONS[tone]} sizePx={20} />
      <div>
        <p className="banner__title">{title}</p>
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

type SlotProps = {
  /** What P1 builds here, in a few words. */
  label: string;
  /** Where its data comes from, usually an endpoint from contracts/api.md. */
  source?: string;
  minHeightPx?: number;
};

/**
 * A dashed "build here" box: space left on purpose for P1 to design and wire up.
 * Dev-only, so its text is not translated. Search the code for "<Slot" to list every open spot,
 * and delete each one as it is built.
 */
export function Slot({ label, source, minHeightPx }: SlotProps) {
  return (
    <div className="slot" style={minHeightPx ? { minHeight: minHeightPx } : undefined}>
      <span className="slot__label">P1 · {label}</span>
      {source && <span>{source}</span>}
    </div>
  );
}
