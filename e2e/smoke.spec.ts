// @smoke: quick checks that change nothing, safe to run against the live app at any time.
// They catch a frontend that can't reach the API, deep links that 404, and an unseeded database.

import { expect, test } from "@playwright/test";
import { ACCOUNTS, openPhone } from "./helpers";

/** The app's own page shell. A server page (the record or verify page) never contains it. */
const APP_SHELL_MARKER = '<div id="root">';

test.describe("@smoke", () => {
  test("the API answers on the app's own address", async ({ request }) => {
    const answer = await request.get("/api/health");
    expect(answer.status()).toBe(200);
    expect(await answer.json()).toEqual({ status: "ok" });
  });

  test("a link to any screen opens the app, not a 404", async ({ request }) => {
    const answer = await request.get("/login");
    expect(answer.status()).toBe(200);
    expect(await answer.text()).toContain(APP_SHELL_MARKER);
  });

  test("verify links reach the server's page, not the app", async ({ request }) => {
    const answer = await request.get("/verify/NOCODE");
    expect(answer.headers()["content-type"]).toContain("text/html");
    expect(await answer.text()).not.toContain(APP_SHELL_MARKER);
  });

  test("first visit shows the language picker", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/welcome$/);
    await expect(page.getByRole("radio", { name: "isiZulu" })).toBeVisible();
  });

  test("a customer logs in and sees home, their jobs and who works nearby", async ({ browser }) => {
    const customer = await openPhone(browser, ACCOUNTS.lindiwe);
    await expect(customer.getByText("Hi, Lindiwe")).toBeVisible();
    await expect(customer.getByText("Something went wrong")).toHaveCount(0);
    await customer.goto("/nearby");
    await expect(customer.getByRole("heading", { name: /within \d+ km/ })).toBeVisible();
  });

  test("a provider logs in and sees the feed, a profile and their record", async ({ browser }) => {
    const provider = await openPhone(browser, ACCOUNTS.nosipho);
    await expect(provider.getByRole("heading", { name: "New jobs" })).toBeVisible();
    await provider.goto("/providers/prov_002");
    await expect(provider.getByText("Trust range")).toBeVisible();
    await provider.goto("/my-record");
    await expect(provider.getByText(/Towards ARPL/)).toBeVisible();
  });
});
