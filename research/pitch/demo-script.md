# Demo script: two phones, one story, about 2 minutes

**Cast:** Mrs. van Wyk speaks only Afrikaans and has a leaking geyser pipe in Mondeor. Nomsa is an isiZulu-first plumber with no reviews yet.

| # | What happens | Phone | What the audience must notice | Built by |
|---|---|---|---|---|
| 1 | She photographs the leak and types in Afrikaans. The app suggests "Plumbing, small job". | Van Wyk | It understood the photo | Roles 2, 3 |
| 2 | Nomsa gets the job in isiZulu through the newcomer slot. She quotes R450 for Tuesday 10:00. | Nomsa → Van Wyk | The price and time come through exactly | Roles 1, 2, 4 |
| 3 | Mrs. van Wyk tries to send "o82 one two three…" and the app masks it. | Van Wyk → Nomsa | Nobody can swap numbers early | Role 3 |
| 4 | She accepts, Nomsa confirms, and the address and phone numbers unlock on both phones. | Both | Details unlock only after both approve | Roles 2, 3 |
| 5 | Cut to the fairness chart. | Slide | Newcomers get a fair chance | Role 4 |

## Before every rehearsal

- [ ] `POST /api/demo/reset` (or the reset button, once Role 2 adds it)
- [ ] `.env`: `TRANSLATION_BACKEND` is a real backend, not `echo`
- [ ] `VITE_USE_MOCK_API=false`
- [ ] Phone 1 opens `http://<laptop-ip>:5173/?as=customer-van-wyk`, phone 2 opens `/?as=provider-nomsa`

## Backup plan (pitch day)

- [ ] Backup video of the full demo, on a laptop and on a USB stick
- [ ] Phones charged, hotspot ready, and tested on the venue Wi-Fi when we arrive
- [ ] Have a first-language isiZulu speaker and an Afrikaans speaker check the on-screen wording
