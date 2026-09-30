// Small labels for codes from the contract: trade, ID badge and job state.

import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import type { IdBadge, JobState, TradeId } from "../api/types";
import { Chip, type ChipTone, type IconName } from "../ui";

/**
 * Icon for each trade, shown beside its name for people who read slowly.
 * Trades without a specific icon fall back to the wrench.
 */
const TRADE_ICONS: Partial<Record<TradeId, IconName>> = {
  plumbing: "droplet",
  electrical: "bolt",
  carpentry: "hammer",
  welding: "flame",
  bricklaying: "layers",
  mechanic: "car",
  roofing: "layers",
  tiling: "grid",
  cabinetmaking: "hammer",
  painting: "paintRoller",
  appliance_repair: "washer",
  groundskeeping: "trees",
};
const DEFAULT_TRADE_ICON: IconName = "wrench";

/** A trade's name in the reader's language, falling back to its id until the locale has it. */
export function getTradeLabel(t: TFunction, trade: TradeId) {
  return t(`trade.${trade}`, { defaultValue: trade });
}

/** A trade name with its icon. */
export function TradeChip({ trade, tone }: { trade: TradeId; tone?: ChipTone }) {
  const { t } = useTranslation();
  return (
    <Chip tone={tone} icon={TRADE_ICONS[trade] ?? DEFAULT_TRADE_ICON}>
      {getTradeLabel(t, trade)}
    </Chip>
  );
}

const ID_BADGE_TONES: Record<IdBadge, ChipTone> = {
  none: "outline",
  id_number: "default",
  home_affairs: "lime",
};

/** How far a provider's identity has been checked: none, ID number, or Home Affairs. */
export function IdBadgeChip({ badge }: { badge: IdBadge }) {
  const { t } = useTranslation();
  return (
    <Chip tone={ID_BADGE_TONES[badge]} icon={badge === "none" ? undefined : "shield"}>
      {t(`idBadge.${badge}`)}
    </Chip>
  );
}

const JOB_STATE_TONES: Partial<Record<JobState, ChipTone>> = {
  confirmed: "lime",
  in_progress: "lime",
  cancelled: "outline",
};

/** A job's state as a chip, for lists. Confirmed and in-progress jobs stand out in lime. */
export function JobStateChip({ state }: { state: JobState }) {
  const { t } = useTranslation();
  return <Chip tone={JOB_STATE_TONES[state]}>{t(`jobState.${state}`)}</Chip>;
}
