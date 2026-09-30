// The provider's own screens: ID verification, the work record and its exports, and logging a
// job done outside the app.

import { expect, test } from "@playwright/test";
import { ACCOUNTS, IS_LIVE, openPhone } from "./helpers";

/** On the demo verifier's register as Sipho Dlamini (api/fixa_api/identity.py). */
const SIPHO_ID_NUMBER = "8506150123089";
const TYPO_ID_NUMBER = "8506150123088";

test("ID verification catches a typo, then Home Affairs confirms", async ({ browser }) => {
  const sipho = await openPhone(browser, ACCOUNTS.sipho);
  await sipho.goto("/verify-id");
  await sipho.getByLabel("I agree to this check").check();
  await sipho.getByLabel("SA ID number").fill(TYPO_ID_NUMBER);
  await sipho.getByRole("button", { name: "Check number" }).click();
  await expect(sipho.getByText("There's a typo in this number")).toBeVisible();

  await sipho.getByLabel("SA ID number").fill(SIPHO_ID_NUMBER);
  await sipho.getByRole("button", { name: "Check number" }).click();
  await expect(sipho.getByText("This number looks right")).toBeVisible();
  await sipho.getByLabel("Your names, as on your ID").fill("Sipho Dlamini");
  await sipho.getByRole("button", { name: "Check with Home Affairs" }).click();
  await expect(sipho.getByText("Home Affairs confirmed who you are.")).toBeVisible();
  await sipho.goto("/me");
  await expect(sipho.getByText("Home Affairs verified")).toBeVisible();
});

test("my record shows ARPL progress, exports a PDF and offers the record link", async ({ browser }) => {
  const nosipho = await openPhone(browser, ACCOUNTS.nosipho);
  await nosipho.goto("/my-record");
  await expect(nosipho.getByText(/Towards ARPL/)).toBeVisible();
  await expect(nosipho.locator(".figure--hero").first()).not.toHaveText(/^0/);

  const pdf = nosipho.waitForResponse((answer) => answer.url().includes("/api/record/exports/"));
  await nosipho.getByRole("button", { name: "Export for ARPL" }).click();
  expect((await pdf).headers()["content-type"]).toContain("application/pdf");
  await expect(nosipho.getByText("Verify code")).toBeVisible();
  await expect(nosipho.getByRole("button", { name: "Share record link" })).toBeVisible();

  const recordPage = await nosipho.request.get("/record/prov_003");
  expect(recordPage.status()).toBe(200);
  expect(await recordPage.text()).toContain("Nosipho");
});

test("an export with no confirmed jobs says why", async ({ browser }) => {
  const newcomer = await openPhone(browser, ACCOUNTS.noJobsProvider);
  await newcomer.goto("/my-record");
  await newcomer.getByRole("button", { name: "Export for ARPL" }).click();
  await expect(newcomer.getByText("There are no confirmed jobs on your record yet.", { exact: false })).toBeVisible();
});

test("logging a past job waits for the customer's SMS", async ({ browser }) => {
  // With a live Africa's Talking key this texts a real number, so live runs skip it unless asked.
  test.skip(IS_LIVE && !process.env.E2E_ALLOW_SMS, "sends an SMS; set E2E_ALLOW_SMS=1 to run it on live");
  const sipho = await openPhone(browser, ACCOUNTS.sipho);
  await sipho.goto("/off-app-jobs/new");
  await sipho.getByLabel("Customer's phone number").fill(`083 555 ${1000 + Math.floor(Math.random() * 9000)}`);
  await sipho.getByLabel("What did you do?").fill("Replaced a geyser valve");
  await sipho.getByLabel("Date").fill("2026-09-20");
  await sipho.getByLabel("Suburb").fill("Braamfontein");
  await sipho.getByLabel("Amount (rands)").fill("650");
  await sipho.getByRole("button", { name: "Send for confirmation" }).click();
  await expect(sipho.getByText("Waiting for the customer")).toBeVisible();
});
