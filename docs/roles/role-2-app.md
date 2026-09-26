# Role 2: App and demo screens

**You own** `frontend/` and `backend/fixa/seed/demo_data.py`, the people in the demo.

**Your part of the demo:** everything the audience sees on the two phones. Build it for a cheap Android phone first: big buttons, icons beside text, and little typing.

## Already in place

| File | State |
|---|---|
| `vite.config.js` | Listens on Wi-Fi (for phones) and proxies `/api` to the backend |
| `public/manifest.webmanifest`, `sw.js`, `icons/` | Installable PWA, with placeholder icons |
| `src/api/client.js` | One function per endpoint. Screens call `api.xyz()`, never `fetch`. |
| `src/api/mockData.js` | Fake data, used while `VITE_USE_MOCK_API=true` in `.env` |
| `src/App.jsx` | Simple screen switching. Each **tab** remembers its own demo user. |
| `src/screens/ChooseUserScreen.jsx` | ✅ Works. Lists the demo users and shows whether the backend is up. |
| `src/screens/JobListScreen.jsx` | Loads and lists jobs. This is the pattern to copy. |
| `src/screens/PostJobScreen.jsx`, `JobDetailScreen.jsx` | Placeholders with a TODO list in the header comment |
| `src/components/MessageBubble.jsx`, `TradeIcon.jsx` | Basic versions, with TODO lists |
| `src/hooks/usePolling.js` | Refreshes data every 2 s, for chat and the job list |
| `src/i18n/strings.js` | UI text per language, falling back to English |

## Your week

| Day | Deliverable |
|---|---|
| Sun 27 | Every screen clickable with mock data: language picker, post job, job list, quotes, chat, unlock. |
| Mon 28 | Chat bubble done: "See original" toggle, `[***]` shown as a "number hidden" chip, "unsure" marker, scam warning banner. |
| Tue 29 | Set `VITE_USE_MOCK_API=false` and connect to Role 3's real endpoints. Finish the seed profiles. |
| Wed 30 | Full demo on two real phones, twice. |
| Thu 1 | Polish. Record the backup demo video. |

## Tips

- **Test both sides on one laptop** by opening two tabs: `localhost:5173/?as=customer-van-wyk` and `localhost:5173/?as=provider-nomsa`.
- **Phones:** use the same Wi-Fi and open the Network address Vite prints. If Windows asks, allow Node through the firewall.
- **Times:** `new Intl.DateTimeFormat(languageCode, { weekday: "long", hour: "2-digit", minute: "2-digit" })` shows "Dinsdag" or "ULwesibili" with no translation needed.
- **Prices:** always format them as `R${amountInRand}` so they look the same in every language.
- **UI words:** get a first-language speaker to write the isiZulu and Afrikaans strings. Don't machine-translate your own buttons.
- **Photos:** `<input type="file" accept="image/*" capture="environment">` opens the camera on Android.
- **Reset:** a small "Reset demo" button that calls `api.resetDemo()` saves time in rehearsals.

## Contracts you must keep

- JSON shapes match [docs/api-contract.md](../api-contract.md). If you need a new field, ask Role 3 and update the doc together.
- Keep `mockData.js` in the same shape as the real API, so switching the flag doesn't break anything.
