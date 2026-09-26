// Fake backend for building screens before the real one works (VITE_USE_MOCK_API=true).
// Same function names and JSON shapes (camelCase) as client.js's realApi.
// TODO (Role 2): add whatever fixtures your screens need; keep the shapes matching docs/api-contract.md.

import { MASKED_CONTACT_TOKEN } from "../constants.js";

const users = [
  { id: "customer-van-wyk", displayName: "Mrs. van Wyk", role: "customer", preferredLanguage: "af", area: "Mondeor" },
  {
    id: "provider-nomsa", displayName: "Nomsa", role: "provider", preferredLanguage: "zu", area: "Mondeor",
    trades: ["plumbing"], badges: ["id_checked"], completedJobCount: 0, ratingSum: 0, ratingCount: 0,
  },
];

const jobs = [
  {
    id: "job-demo", customerId: "customer-van-wyk", trade: "plumbing", size: "small",
    description: "My geiser se pyp lek. Kan iemand Dinsdag kom?", descriptionLanguage: "af",
    area: "Mondeor", photoId: null, state: "quoted", offeredProviderIds: ["provider-nomsa"],
    acceptedQuoteId: null, assignedProviderId: null, createdAt: "2026-09-29T08:00:00",
  },
];

const quotes = [
  {
    id: "quote-demo", jobId: "job-demo", providerId: "provider-nomsa", amountInRand: 450,
    proposedStartAt: "2026-09-29T10:00:00", createdAt: "2026-09-29T08:05:00",
  },
];

// isiZulu/Afrikaans wording is the illustrative text from the sprint plan - not yet checked.
const messages = [
  {
    id: "message-1", jobId: "job-demo", senderId: "provider-nomsa", recipientId: "customer-van-wyk",
    originalText: "Ngingayilungisa nge-R450, ngoLwesibili ngo-10:00.", originalLanguage: "zu",
    translatedText: "Ek kan dit regmaak vir R450, Dinsdag om 10:00.", translatedLanguage: "af",
    translationFlags: [], scamWarnings: [], containsMaskedContact: false, createdAt: "2026-09-29T08:06:00",
  },
  {
    id: "message-2", jobId: "job-demo", senderId: "customer-van-wyk", recipientId: "provider-nomsa",
    originalText: `Bel my op ${MASKED_CONTACT_TOKEN}`, originalLanguage: "af",
    translatedText: `[zu] Bel my op ${MASKED_CONTACT_TOKEN}`, translatedLanguage: "zu",
    translationFlags: ["backend_uncertain"], scamWarnings: [], containsMaskedContact: true,
    createdAt: "2026-09-29T08:07:00",
  },
];

const NOT_IN_MOCK = (name) => () => Promise.reject(new Error(`${name} is not in the mock API yet`));

export const mockApi = {
  listUsers: async () => users,
  getCurrentUser: async () => users[0],
  updateMyLanguage: NOT_IN_MOCK("updateMyLanguage"),
  listLanguages: async () => [
    { code: "af", name: "Afrikaans", isPilot: true },
    { code: "zu", name: "isiZulu", isPilot: true },
    { code: "en", name: "English", isPilot: true },
  ],
  listTrades: async () => [{ tradeId: "plumbing", englishLabel: "Plumbing", icon: "🔧" }],
  suggestTrade: async () => ({ trade: "plumbing", size: "small", confidence: 0.9, source: "mock" }),
  listJobs: async () => jobs,
  createJob: NOT_IN_MOCK("createJob"),
  listQuotes: async () => quotes,
  createQuote: NOT_IN_MOCK("createQuote"),
  acceptQuote: NOT_IN_MOCK("acceptQuote"),
  confirmJob: NOT_IN_MOCK("confirmJob"),
  unlockContactDetails: NOT_IN_MOCK("unlockContactDetails"),
  getContactDetails: NOT_IN_MOCK("getContactDetails"),
  listMessages: async () => messages,
  sendMessage: NOT_IN_MOCK("sendMessage"),
  resetDemo: async () => null,
};
