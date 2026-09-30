# Fixa API contract

> **DRAFT for the Day 1 morning meeting.** Change anything here together, then delete this line.
> After that, a contract only changes with a heads-up in the group chat, and `api.md` and `fixtures/` change in the same commit.

- Every endpoint starts with `/api`, except the plain-HTML link pages (`/verify/…`, `/record/…`).
- JSON uses **snake_case**, the same names as the Python package functions.
- Auth: send `Authorization: Bearer <token>` from `POST /api/auth/verify`. Demo users log in with OTP `123456`.
- Text a user reads (job problems, chat, warnings) comes back already translated into **their** language, with the original alongside.
- isiZulu wording in the fixtures is placeholder text. A native speaker checks it before it goes on screen.
- Each endpoint's example response is in `fixtures/`. The app's MSW mocks serve these files, and the API returns them until the real code exists.

## Codes

| Code | Values |
|---|---|
| Language | `en` · `zu` · `xh` |
| Trade | `electrical` · `plumbing` · `carpentry` · `welding` · `bricklaying` · `mechanic` · `roofing` · `tiling` · `cabinetmaking` · `painting` · `appliance_repair` · `groundskeeping` · `other` |
| Job size | `small` · `medium` · `large` |
| Urgency | `low` · `normal` · `urgent` |
| Job state | `posted` → `quoting` → `quote_accepted` → **`confirmed`** → `in_progress` → `done` → `followed_up`, plus `cancelled` |
| Quote state | `open` · `accepted` · `declined` · `withdrawn` |
| ID badge | `none` · `id_number` · `home_affairs` |
| Record mode | `arpl` · `statement` |

**Job states:**

- Contact details unlock at `confirmed`.
- If the provider declines, the job goes back to `quoting`.
- Any state can move to `cancelled`.

**Privacy gate:**

- Before `confirmed`, every response uses `JobPublic`, which shows the suburb and the problem only.
- `JobUnlocked` adds the address, both phone numbers and the provider's photo. Only the job's customer and its confirmed provider ever receive it.

**Where a job is (`location` on `POST /api/jobs`):**

- By default a job is at the customer's home. The customer can drop a pin instead (a parent's house, a rental).
- The server names the pin itself (OpenStreetMap Nominatim: one request a second at most, cached, with a real User-Agent). The `suburb` the phone sends is ignored.
- The job keeps its own point, suburb and street address. The ranked list, the feed's distances and the price range all use the job's point and suburb, not the customer's home.
- Privacy is unchanged: before `confirmed`, providers see the suburb and a rounded distance only. Exact coordinates are never sent to anyone, and the street address arrives only in `JobUnlocked`.

**Browsing nearby providers (`GET /api/providers`):**

- It's for looking, not picking. There's no way to contact or book from the list: hiring still goes through a job and its ranked list.
- `trade` is required. `lang` (optional) keeps only providers who speak it. `radius_km` (optional, default `10`) is how far from the customer's home counts as near. It must be more than 0 and at most `30`, otherwise the answer is 422.
- Distances are from the customer's home, rounded to 0.1 km as in the ranked list. The list is nearest first and never ordered by trust.
- Each row is a `NearbyProvider`: it has no `trust`, so the list can't turn into a leaderboard. Trust shows on the profile and in a job's ranked list.

## Endpoints

| Method | Path | Who | Body / query | Response (fixture) |
|---|---|---|---|---|
| GET | `/api/health` | anyone | | `health.json` |
| POST | `/api/auth/otp` | anyone | `{phone}` | 204 |
| POST | `/api/auth/verify` | anyone | `{phone, otp}` | `auth_verify.json` |
| GET | `/api/me` | user | | `me.json` |
| PATCH | `/api/me` | user | `{lang}` | `me.json` |
| POST | `/api/jobs/understand` | customer | `{text, lang}` | `job_intent.json` |
| POST | `/api/photos` | user | multipart `photo` (shrunk on the phone) | `photo.json` |
| POST | `/api/jobs` | customer | `{description, lang, trade, urgency, size, suburb, photo_id?, directions?, location?}` | 201 `job_public.json`. `location` is `{lat, lng}` for a pin away from home; left out, the job is at the customer's home. 422 `place_not_found` outside South Africa, 503 `place_lookup_failed` if the lookup is down |
| GET | `/api/me/area` | customer | | `{suburb, lat, lng}`: the customer's home suburb and its point rounded to 2 decimals (~1 km), to open the job map on |
| GET | `/api/places/reverse` | customer | `?lat=&lng=` | `{suburb, label}`: what a dropped pin is called. Same errors as `location` above |
| GET | `/api/jobs` | user | | `my_jobs.json`: a customer's own jobs, or the jobs a provider quoted on or was picked for, newest first (20 at most). Each is `JobPublic`, or `JobUnlocked` from `confirmed` on |
| GET | `/api/jobs/{job_id}` | job's customer, shortlisted providers | | `job_public.json`, or `job_unlocked.json` from `confirmed` on |
| GET | `/api/jobs/{job_id}/providers` | job's customer | | `ranked_providers.json` |
| GET | `/api/providers` | customer | `?trade=&lang=&radius_km=` | `nearby_providers.json` (for `?trade=plumbing`) |
| GET | `/api/providers/{provider_id}` | user | | `provider_profile.json` |
| GET | `/api/feed` | provider | | `feed.json` |
| GET | `/api/price-range` | user | `?trade=&size=&suburb=` | `price_range.json`, or `null` below 8 quotes |
| POST | `/api/jobs/{job_id}/quotes` | provider | `{amount_rands, when, message?}` | 201 `quote.json` |
| GET | `/api/jobs/{job_id}/quotes` | job's customer, quoting provider | | `quotes.json` |
| POST | `/api/quotes/{quote_id}/accept` | job's customer | | `job_public.json` (state `quote_accepted`) |
| POST | `/api/jobs/{job_id}/confirm` | accepted provider | | `job_unlocked.json` (state `confirmed`) |
| POST | `/api/jobs/{job_id}/decline` | accepted provider | | `job_public.json` (state `quoting`) |
| POST | `/api/jobs/{job_id}/cancel` | job's customer | | `job_public.json` (state `cancelled`) |
| GET | `/api/jobs/{job_id}/messages` | job parties | `?after=<message_id>` (polled every 3 s) | `messages.json` |
| POST | `/api/jobs/{job_id}/messages` | job parties | `{text, provider_id?}`: a customer with several quoting providers says who it's for | 201 `message.json` |
| POST | `/api/identity/check-number` | provider | `{id_number}` (offline check) | `id_number_check.json` |
| POST | `/api/identity/verify` | provider | `{id_number, names, consent: true}` | `id_result.json` |
| POST | `/api/off-app-jobs` | provider | `{customer_phone, trade_task, date, suburb, amount_rands?}` | 201 `off_app_job.json` |
| POST | `/api/sms/inbound` | Africa's Talking webhook | form fields from Africa's Talking | 200 |
| POST | `/api/record/export` | provider | `{mode}` | `record_export.json` |
| GET | `/api/record/summary` | provider | | `record_summary.json`: the ARPL trade (null if none), months of confirmed experience in it as the ARPL record counts them, calendar months with work, and confirmed jobs |
| GET | `/record/{provider_id}` | anyone with the link | | Plain-HTML work record page, no JavaScript |
| GET | `/verify/{code}` | anyone with the link | | Plain-HTML verify page, no JavaScript |

## Shapes

These are the shapes of the objects in the fixtures, and each fixture is the source of truth for its shape.

- **User** (`me.json`): `id, role (customer|provider), display_name, lang, suburb, id_badge`
- **JobPublic**: `id, state, trade, size, urgency, suburb, problem, problem_original, problem_lang, translation_flagged, photo_url, distance_km, created_at`
- **JobUnlocked**: JobPublic plus `address, directions, customer_phone, provider_phone, provider_photo_url`
- **RankedProvider**: `provider_id, display_name, trades, distance_km, is_newcomer, id_badge, evidence {jobs, repeat_customers, photos, off_app_confirmed}, trust {score, low, high, label}`
- **NearbyProvider**: `provider_id, display_name, suburb, trades, langs, distance_km, is_newcomer, id_badge, evidence {jobs, repeat_customers, photos, off_app_confirmed}` (no `trust`)
- **Quote**: `id, job_id, provider_id, amount_rands, when, message, state, created_at`
- **Message**: `id, job_id, sender_id, recipient_id, text, original, original_lang, flagged, flag_reason, contacts_hidden, scam_warnings, sent_at`. A customer has one thread per quoting provider; `sender_id` and `recipient_id` say which.
- **PriceRange**: `trade, size, suburb, low_rands, high_rands, n_quotes`

## Safety and notifications

Added on 30 Sep for the demo (branch `safety-features`). Every route needs a login; job routes only work for the job's customer and its picked provider (404 for anyone else).

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/me/trusted-contact` | | `{name, phone}` or `null` |
| PUT | `/api/me/trusted-contact` | `{name, phone}` | `{name, phone}` |
| POST | `/api/jobs/{job_id}/panic` | `{lat?, lng?}` | 201 **PanicResult**. Texts the trusted contact a map link; the other person is never told |
| POST | `/api/jobs/{job_id}/on-my-way` | | `{told: true}`. Picked provider, confirmed job only; the customer gets an inbox item |
| GET | `/api/jobs/{job_id}/safety-timer` | | **SafetyTimer** or `null` (the latest one) |
| POST | `/api/jobs/{job_id}/safety-timer` | `{minutes}` (1, 15, 30, 60, 120 or 240) | 201 **SafetyTimer**. When it's up it asks "Are you OK?"; unanswered by `alert_at`, it texts the trusted contact. Check-in starts one for the provider (2 h small job, 4 h medium or large); check-out stops it |
| POST | `/api/jobs/{job_id}/safety-timer/safe` | | **SafetyTimer** (`state: safe`) |
| POST | `/api/jobs/{job_id}/location` | `{moment, lat, lng, accuracy_m?}` | 201. `moment`: `on_my_way`, `check_in`, `check_out`, `done`, `panic` or `timer_start` |
| GET | `/api/jobs/{job_id}/locations` | | **KeyMoment[]**: distance from the job only, never coordinates; a panic or a timer start only for whoever made it |
| GET | `/api/notifications` | | **Inbox**, newest first, in the reader's language |
| POST | `/api/notifications/read` | | **Inbox**, all read |
| POST | `/api/notifications/{id}/read` | | **Inbox** |
| GET | `/api/push/key` | | `{public_key}`, or 404 when push isn't set up |
| POST | `/api/push/subscriptions` | a browser `PushSubscription.toJSON()` | 201 |
| POST | `/api/push/subscriptions/remove` | `{endpoint}` | `{subscribed: false}` |

- **PanicResult**: `alert_id, contact ({name, phone} or null), sms_sent, whatsapp_url (or null), location_shared, emergency_numbers [{label, number}]`. `sms_sent` is true only when the SMS provider accepted the text; `whatsapp_url` opens WhatsApp with the same alert for the contact
- **SafetyTimer**: `id, state (running|asking|safe|missed), reason (manual|check_in), started_at, due_at, alert_at`. From GET, a missed timer also has `contact_notified` (the SMS really went) and `whatsapp_url` (or null)
- **KeyMoment**: `moment, role, name, is_me, at, distance_km`
- **Inbox**: `unread, items [{id, kind, title, body, job_id, created_at, read}]`. Kinds: `quote_received, quote_accepted, job_confirmed, job_declined, message, on_my_way, checked_in, checked_out, job_done, panic_sent, panic_not_sent, panic_no_contact, timer_check, timer_missed, timer_missed_not_sent, timer_missed_no_contact`
