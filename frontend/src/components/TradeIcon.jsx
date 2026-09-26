// Icon shown beside every trade label, so people who read less can still find their trade.
// TODO (Role 2): swap the emoji for clear, simple icons once the pilot trades are picked.

const ICONS_BY_TRADE_ID = {
  plumbing: "🔧",
  electrical: "⚡",
  painting: "🎨",
};

const UNKNOWN_TRADE_ICON = "🛠️";

export default function TradeIcon({ tradeId }) {
  return (
    <span className="trade-icon" aria-hidden="true">
      {ICONS_BY_TRADE_ID[tradeId] ?? UNKNOWN_TRADE_ICON}
    </span>
  );
}
