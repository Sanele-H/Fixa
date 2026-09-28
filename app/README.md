# Fixa app (P1)

A UI scaffold: the visual style, a small component kit, and every main screen laid out with sample data.
The behaviour, the data layer, and the final design of each screen are yours.

Run `npm run dev` from the repo root, then open **http://localhost:5173/dev/screens** (development only). It lists every screen and has a customer/provider switch.

## Installing the app

The manifest and service worker come from `vite-plugin-pwa` in [vite.config.ts](vite.config.ts). The service worker only runs in production builds, so the dev server never shows Chrome's install icon. To try installing on a laptop, run `npm run build:app` from the repo root, then `npm --prefix app run preview` and open http://localhost:4173. On a phone, use the live site, or keep the preview running and run `cloudflared tunnel --url http://localhost:4173` (`npm run tunnel` points at the dev server, which has no service worker). If the icon doesn't appear, DevTools → Application → Manifest lists what's missing.

## The look

Everything comes from [src/styles/tokens.css](src/styles/tokens.css). Change a token and the whole app follows.

| Token | Means |
|---|---|
| Grey canvas, soft rounded cards | the base |
| Black (`--color-inverse`) | whatever is selected, and the one main action on a screen |
| Lime (`--color-lime`) | go / new / positive: calls to action, newcomers, ARPL progress, unlocked contact details |
| Lavender (`--color-lavender`) | trust and information: trust ranges, translation notes |
| Big light numbers (`.figure`, `.figure--hero`) | the clock-face style for prices, distances and counts |

The font is Space Grotesk, loaded from Google Fonts in `index.html`. Self-host it so it works offline.

## Where things are

```
src/styles/      tokens.css (design tokens), base.css (reset)
src/ui/          the kit: Button, IconButton, Card, RowCard, Chip, Segmented, TextField,
                 Banner, Slot, Figure, Stat, Avatar, ProgressMeter, TrustRange, BottomNav, Icon
src/components/  Fixa pieces: ProviderCard + EvidenceStrip, JobCard, QuoteCard, ContactCard,
                 JobStateRuler, MessageBubble, TradeChip / IdBadgeChip / JobStateChip
src/screens/     one file per route, each lazy-loaded
src/app/         paths.ts (every URL), router.tsx, layouts.tsx (tab bar, redirects)
src/i18n/        i18next setup; locales/en.json has every string
src/api/types.ts TypeScript shapes copied from contracts/api.md
src/dev/         samples.ts (fixture data for the screens) and the /dev/screens page
```

## What's left for you

- **Slots.** Dashed boxes labelled `P1 · …` mark space left on purpose. Each one says what goes there and which endpoint feeds it. To list them all, run `grep -rn "<Slot" src`. Delete each one as you build it.
- **Not set up yet:**
  - MSW
  - TanStack Query: replace every import of `src/dev/samples.ts`, then delete that file
  - real login: `src/session/SessionContext.tsx` is a stand-in that only remembers the role
- **isiZulu and isiXhosa:** `zu.json` and `xh.json` are empty until a native speaker checks the strings. Missing strings show in English.
- **Contract gaps found while laying out screens.** Raise these with the team:
  - No endpoint lists a customer's own jobs (Home screen).
  - No endpoint returns the "My record" contents or months of experience.
  - The provider profile has no list of work photos.
  - "Well below the range" for the underpricing warning isn't decided (P4). For now the Quote screen warns below the range's low end.

## Rules the scaffold already follows

- Every string a user reads goes through `t()`. Only `Slot` text and `/dev/screens` are untranslated, because they never ship.
- CSS uses tokens only, never raw colours.
- Contact details show only when the server sent them (`isJobUnlocked`). The app never hides them as a security measure.
- No star ratings. Trust is a range; a newcomer gets a hatched "not known yet" bar.
- Back arrows go to a path, not `history.back()`, because screens open from shared links.
- App paths avoid `/api`, `/record/…` and `/verify/…`, which belong to the server.
- First load is about 130 KB gzipped against the 300 KB budget. `npm run build:app` prints the sizes.
