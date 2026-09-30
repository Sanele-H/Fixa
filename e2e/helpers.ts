// Shared pieces for the end-to-end tests: where the app is, the demo accounts, and a "phone"
// (a fresh browser context) that's logged in as one of them.

import type { APIRequestContext, Browser, Page } from "@playwright/test";

const LOCAL_URL = "http://localhost:5173";

/** The frontend's address. The app calls /api on the same address, so this reaches the API too. */
export const BASE_URL = (process.env.E2E_BASE_URL ?? LOCAL_URL).replace(/\/$/, "");
export const IS_LIVE = BASE_URL !== LOCAL_URL;

/** The seeded demo accounts (data/seed). Every account's code is DEMO_OTP. */
export const ACCOUNTS = {
  lindiwe: "082 000 0001", // customer in Braamfontein, English
  followUpCustomer: "082 000 0021", // a customer with finished jobs from months ago, never followed up
  thabo: "071 000 0001", // plumber, English
  sipho: "071 000 0002", // plumber, isiZulu
  nosipho: "071 000 0003", // plumber with about 4 years of confirmed work
  noJobsProvider: "071 000 0029", // a provider with nothing confirmed yet
} as const;

export const DEMO_OTP = process.env.E2E_OTP ?? "123456";

type Language = "en" | "zu" | "xh";

/**
 * Opens a new "phone" with its app language already picked, and logs in as `phone`.
 * Resolves once the home tab (customers) or the feed (providers) is showing.
 */
export async function openPhone(browser: Browser, phone: string, language: Language = "en"): Promise<Page> {
  const context = await browser.newContext();
  await context.addInitScript((lang) => localStorage.setItem("fixa.lang", lang), language);
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("Phone number").fill(phone);
  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/(home|feed)$/);
  return page;
}

/** Calls the API from inside a logged-in phone, with its token, and returns the JSON answer. */
export async function callApi<T>(page: Page, method: string, path: string, body?: unknown): Promise<T> {
  return page.evaluate(
    async ({ method, path, body }) => {
      const answer = await fetch(path, {
        method,
        headers: { Authorization: `Bearer ${localStorage.getItem("fixa.token")}`, "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      return answer.json();
    },
    { method, path, body },
  );
}

/** Logs in over the API alone and returns the Authorization header, for setting up a test. */
export async function readAuthHeader(request: APIRequestContext, phone: string) {
  const answer = await request.post("/api/auth/verify", { data: { phone, otp: DEMO_OTP } });
  const { token } = (await answer.json()) as { token: string };
  return { Authorization: `Bearer ${token}` };
}

/** A text no other run has used, so a test finds its own job among everything else. */
export function makeUniqueText(prefix: string) {
  return `${prefix} ${Date.now().toString(36)}`;
}
