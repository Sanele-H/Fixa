// Looking before hiring: "Who works near you" with its filters, and profiles opened from it or
// from a job's ranked list.

import { expect, test } from "@playwright/test";
import { ACCOUNTS, openPhone } from "./helpers";

test("the nearby list filters on the server, and a profile goes back to it", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  await lindiwe.goto("/nearby");
  const count = lindiwe.getByRole("heading", { name: /within 10 km/ });
  const everyone = await count.innerText();

  await lindiwe.getByRole("radio", { name: "isiZulu" }).click();
  await expect(count).not.toHaveText(everyone);

  const firstCard = lindiwe.locator("a[href*='/providers/']").first();
  const name = (await firstCard.locator("h2").innerText()).trim();
  await firstCard.click();
  await expect(lindiwe.getByRole("heading", { name })).toBeVisible();
  await expect(lindiwe.getByText("Trust range")).toBeVisible();
  await expect(lindiwe.getByText("Describe a job")).toBeVisible();
  await lindiwe.getByRole("link", { name: "Back" }).first().click();
  await expect(lindiwe).toHaveURL(/\/nearby$/);
});

test("a profile opened from a ranked list goes back to that list", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  await lindiwe.goto("/jobs/job_001/providers");
  await lindiwe.locator("a[href*='/providers/']").first().click();
  await expect(lindiwe.getByText("Trust range")).toBeVisible();
  await expect(lindiwe.getByRole("link", { name: "Back" }).first()).toHaveAttribute("href", "/jobs/job_001/providers");
});
