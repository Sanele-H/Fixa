// The demo's main story on two phones: Lindiwe posts a job with a photo, Thabo quotes from his
// feed, she accepts, he confirms, and both phones unlock the contact details by themselves.

import path from "node:path";
import { expect, test } from "@playwright/test";
import { ACCOUNTS, makeUniqueText, openPhone } from "./helpers";

const PHOTO_PATH = path.join(__dirname, "..", "app", "public", "icons", "icon-512.png");

test("a job goes from posted to confirmed across two phones", async ({ browser }) => {
  const problem = makeUniqueText("Kitchen tap leaking under the sink");
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  const thabo = await openPhone(browser, ACCOUNTS.thabo);

  await test.step("Lindiwe describes the job, adds a photo and posts", async () => {
    await lindiwe.goto("/jobs/new");
    await lindiwe.getByLabel("What's the problem?").fill(problem);
    await lindiwe.getByRole("button", { name: "Next" }).click();
    await expect(lindiwe.getByText("We think this is")).toBeVisible();
    await lindiwe.locator('input[type="file"]').setInputFiles(PHOTO_PATH);
    await expect(lindiwe.getByRole("img", { name: "Your photo of the problem" })).toBeVisible({ timeout: 30_000 });
    await lindiwe.getByRole("button", { name: "Post job" }).click();
    await expect(lindiwe).toHaveURL(/\/jobs\/[^/]+\/providers$/);
    await expect(lindiwe.locator("a[href*='/providers/']").first()).toBeVisible();
    await lindiwe.getByRole("link", { name: "Go to my job" }).click();
    await expect(lindiwe.getByText("No quotes yet")).toBeVisible();
  });

  await test.step("Thabo finds it in his feed and quotes, guided by the price range", async () => {
    await thabo.reload();
    await thabo.getByText(problem).click();
    await expect(thabo.getByText("Most accepted quotes nearby")).toBeVisible();
    await thabo.locator("#quote-amount").fill("100");
    await expect(thabo.getByText("You may be underpricing")).toBeVisible();
    await thabo.locator("#quote-amount").fill("450");
    await thabo.getByLabel("When can you come?").fill("2026-10-02T10:00");
    await thabo.getByLabel("Message (optional)").fill("I can bring a new washer.");
    await thabo.getByRole("button", { name: "Send quote" }).click();
    await expect(thabo.getByText("Your quote")).toBeVisible();
  });

  await test.step("the quote reaches Lindiwe by itself, and she accepts", async () => {
    await expect(lindiwe.getByText("I can bring a new washer.")).toBeVisible({ timeout: 30_000 });
    await lindiwe.getByRole("button", { name: "Accept quote" }).click();
    await expect(lindiwe.getByText("Waiting for Thabo to confirm")).toBeVisible();
  });

  await test.step("Thabo sees the accepted quote and confirms; his details unlock", async () => {
    await thabo.goto("/feed");
    await expect(thabo.getByText("A customer accepted your quote")).toBeVisible({ timeout: 30_000 });
    await thabo.getByText(problem).click();
    await thabo.getByRole("button", { name: "Confirm the job" }).click();
    await expect(thabo.getByText("Contact details", { exact: true })).toBeVisible();
  });

  await test.step("Lindiwe's page unlocks by itself, and home shows the job confirmed", async () => {
    await expect(lindiwe.getByText("Contact details", { exact: true })).toBeVisible({ timeout: 30_000 });
    await lindiwe.goto("/home");
    await expect(lindiwe.locator("a", { hasText: problem }).getByText("Confirmed")).toBeVisible();
  });
});

test("a customer can cancel, after being asked once more", async ({ browser }) => {
  const problem = makeUniqueText("Geyser pressure valve dripping");
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  await lindiwe.goto("/jobs/new");
  await lindiwe.getByLabel("What's the problem?").fill(problem);
  await lindiwe.getByRole("button", { name: "Next" }).click();
  await lindiwe.getByRole("button", { name: "Post job" }).click();
  await lindiwe.getByRole("link", { name: "Go to my job" }).click();

  await lindiwe.getByRole("button", { name: "Cancel this job" }).click();
  await lindiwe.getByRole("button", { name: "Yes, cancel it" }).click();
  await expect(lindiwe.getByText("Cancelled", { exact: true })).toBeVisible();
});
