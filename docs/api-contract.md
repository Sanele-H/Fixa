# API contract

This is the agreement between the frontend (Role 2) and the backend (Role 3). The live, clickable version is at http://localhost:8000/docs.

- Every path starts with `/api`.
- JSON uses **camelCase** (`preferredLanguage`). Python uses snake_case, and `ApiModel` converts between them.
- **Demo login:** send `X-User-Id: <user id>` on every request. There are no passwords, and a missing or unknown id gets a 401.
- Endpoints that aren't built yet answer **501** with the TODO that owns them.

| Method | Path | Who | Returns | Status |
|---|---|---|---|---|
| GET | `/health` | anyone | `{status, translationBackend}` | ✅ works |
| GET | `/languages` | anyone | `[{code, name, isPilot}]` | ✅ works |
| GET | `/trades` | anyone | `[{tradeId, englishLabel, icon}]` | ✅ works |
| GET | `/users` | anyone | `[User]`, never with contact details | ✅ works |
| GET | `/users/me` | any user | `User` | ✅ works |
| PATCH | `/users/me` | any user | `User`. Body: `{preferredLanguage}` | ✅ works |
| POST | `/demo/reset` | anyone | 204. Reloads the seed data. | ✅ works |
| POST | `/trade-suggestions` | customer | `{trade, size, confidence, source}`. Multipart `photo`, `?description=` | TODO Role 3 |
| POST | `/jobs` | customer | `Job`. Body: `{trade, size, description, descriptionLanguage, area, photoId?}` | TODO Role 3 |
| GET | `/jobs` | any user | `[Job]`. Customers get their own jobs; providers get jobs they were shortlisted for. | TODO Role 3 |
| GET | `/jobs/{id}/quotes` | job parties | `[Quote]` | TODO Role 3 |
| POST | `/jobs/{id}/quotes` | shortlisted provider | `Quote`. Body: `{amountInRand, proposedStartAt}` | TODO Role 3 |
| POST | `/jobs/{id}/accept` | the job's customer | `Job`. Body: `{quoteId}` | TODO Role 3 |
| POST | `/jobs/{id}/confirm` | accepted provider | `Job` | TODO Role 3 |
| POST | `/jobs/{id}/unlock` | the job's customer | `Job` | TODO Role 3 |
| GET | `/jobs/{id}/contact-details` | job parties | `{userId, phoneNumber, streetAddress?}` for the **other** side. 403 until unlocked. | TODO Role 3 |
| GET | `/jobs/{id}/messages?with_user_id=` | job parties | `[Message]`, oldest first. The frontend polls this every 2 s. | TODO Role 3 |
| POST | `/jobs/{id}/messages` | job parties | `Message`. Body: `{recipientId, text}` | TODO Role 3 |

## Shapes

The source of truth is `backend/fixa/domain/models.py`.

- **Job** has these fields: `id, customerId, trade, size, description, descriptionLanguage, area, photoId, state, offeredProviderIds, acceptedQuoteId, assignedProviderId, createdAt`.
- **Job states**, in order: `posted → quoted → accepted → confirmed → unlocked`.
- **Quote** has `amountInRand` and `proposedStartAt` as structured fields, so translation never touches the price or time.
- **Message** has these fields: `originalText` (already masked), `originalLanguage`, `translatedText`, `translatedLanguage`, `translationFlags` (empty means confident), `scamWarnings` (codes, localised in the frontend) and `containsMaskedContact`.
- The **masked contact token** is `[***]`. The frontend shows it as a "number hidden" chip.

## Error codes

| Code | Meaning |
|---|---|
| 401 | No or unknown `X-User-Id` |
| 403 | Not allowed, for example contact details before unlock or a provider accepting a quote |
| 404 | No such job, quote or user |
| 409 | The job can't move to that state from where it is |
| 501 | Not built yet |
