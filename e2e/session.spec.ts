// Logging in and out, staying logged in, the login guard, and the phone's language going onto
// the account.

import { expect, test } from "@playwright/test";
import { ACCOUNTS, DEMO_OTP, readAuthHeader } from "./helpers";

test("a wrong code is refused, the right one logs in and survives a reload", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Phone number").fill(ACCOUNTS.lindiwe);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByText("Code sent.")).toBeVisible();
  await page.getByLabel("Code from the SMS").fill("000000");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("That phone number or code is wrong.")).toBeVisible();

  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("Hi, Lindiwe")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Hi, Lindiwe")).toBeVisible();
});

test("logging out forgets the session, and guarded screens send you to login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Phone number").fill(ACCOUNTS.lindiwe);
  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.goto("/me");
  await expect(page.getByText("Customer", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("fixa.token"))).toBeNull();
  await page.goto("/home");
  await expect(page).toHaveURL(/\/login$/);
});

test("a provider gets the provider tabs, and a rejected token logs out", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Phone number").fill(ACCOUNTS.thabo);
  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/feed$/);
  await expect(page.getByRole("navigation").getByRole("link")).toHaveText(["Jobs", "Record", "Me"]);

  await page.evaluate(() => localStorage.setItem("fixa.token", "not-a-real-token"));
  await page.goto("/feed");
  await expect(page).toHaveURL(/\/login$/);
});

test("logging in on an English phone puts English on the account", async ({ page, request }) => {
  // Start from Sipho's seeded language, whatever earlier runs left.
  await request.patch("/api/me", { headers: await readAuthHeader(request, ACCOUNTS.sipho), data: { lang: "zu" } });
  await page.addInitScript(() => localStorage.setItem("fixa.lang", "en"));

  await page.goto("/login");
  await page.getByLabel("Phone number").fill(ACCOUNTS.sipho);
  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  const languageSaved = page.waitForResponse((answer) => answer.url().endsWith("/api/me") && answer.request().method() === "PATCH");
  await page.getByRole("button", { name: "Log in" }).click();
  expect((await (await languageSaved).json()).lang).toBe("en");

  // Put his isiZulu back for the demo.
  await request.patch("/api/me", { headers: await readAuthHeader(request, ACCOUNTS.sipho), data: { lang: "zu" } });
});

test("a server that doesn't answer gets a retry screen, not a logout", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Phone number").fill(ACCOUNTS.thabo);
  await page.getByLabel("Code from the SMS").fill(DEMO_OTP);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/feed$/);

  await page.route("**/api/me", (route) => route.abort());
  await page.reload();
  await expect(page.getByText("Can't reach Fixa")).toBeVisible({ timeout: 20_000 });
  await page.unroute("**/api/me");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("navigation")).toBeVisible();
});
