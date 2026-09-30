// After a job is confirmed: the provider checks in, the customer says it was done (or that nobody
// came) and vouches, the "is the fix still working?" question, the report button, and the message
// a refused illegal request gets. These change data, so reseed afterwards.

import { expect, test, type Page } from "@playwright/test";
import { ACCOUNTS, callApi, makeUniqueText, openPhone } from "./helpers";

type JobAnswer = { id: string };
type QuoteAnswer = { id: string };

/** Posts a job as Lindiwe and takes it to `confirmed` with the given provider, over the API. */
async function makeConfirmedJob(lindiwe: Page, provider: Page, problem: string) {
  const job = await callApi<JobAnswer>(lindiwe, "POST", "/api/jobs", {
    description: problem,
    lang: "en",
    trade: "plumbing",
    urgency: "normal",
    size: "small",
    suburb: "Braamfontein",
  });
  const quote = await callApi<QuoteAnswer>(provider, "POST", `/api/jobs/${job.id}/quotes`, {
    amount_rands: 350,
    when: "2026-10-02T10:00:00+02:00",
  });
  await callApi(lindiwe, "POST", `/api/quotes/${quote.id}/accept`);
  await callApi(provider, "POST", `/api/jobs/${job.id}/confirm`);
  return job.id;
}

test("the provider checks in, the customer says it's done and leaves a vouch", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  const thabo = await openPhone(browser, ACCOUNTS.thabo);
  const jobId = await makeConfirmedJob(lindiwe, thabo, makeUniqueText("Bathroom tap dripping"));
  const vouchText = makeUniqueText("Came on time and fixed it well");

  await test.step("Thabo checks in and says the work is finished", async () => {
    await thabo.goto(`/jobs/${jobId}`);
    await thabo.getByRole("button", { name: "I've arrived" }).click();
    await expect(thabo.getByText("Finished the work?")).toBeVisible();
    await thabo.getByRole("button", { name: "I've finished the work" }).click();
    await expect(thabo.getByText("Waiting for the customer to confirm the job is done.")).toBeVisible();
  });

  await test.step("Lindiwe says it's done, and the job finishes", async () => {
    await lindiwe.goto(`/jobs/${jobId}`);
    await expect(lindiwe.getByText("Is the job done?")).toBeVisible();
    await lindiwe.getByRole("button", { name: "Yes, it's done" }).click();
    await expect(lindiwe.getByText("In two weeks we'll ask whether the fix is still working.")).toBeVisible();
  });

  await test.step("she vouches, and the vouch shows on Thabo's profile without her name", async () => {
    await lindiwe.getByLabel("What was it like?").fill(vouchText);
    await lindiwe.getByRole("button", { name: "Send", exact: true }).click();
    await expect(lindiwe.getByText("Thank you for vouching for Thabo.")).toBeVisible();
    await lindiwe.goto("/providers/prov_001");
    await expect(lindiwe.getByText("What customers say")).toBeVisible();
    await expect(lindiwe.getByText(vouchText)).toBeVisible();
    await expect(lindiwe.getByText("Lindiwe", { exact: true })).toHaveCount(0);
  });
});

test("a no-show ends the job, after asking once more", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  const nosipho = await openPhone(browser, ACCOUNTS.nosipho);
  const jobId = await makeConfirmedJob(lindiwe, nosipho, makeUniqueText("Toilet keeps running"));

  await lindiwe.goto(`/jobs/${jobId}`);
  await lindiwe.getByRole("button", { name: "They didn't turn up" }).click();
  await expect(lindiwe.getByText(/Did Nosipho not turn up\?/)).toBeVisible();
  await lindiwe.getByRole("button", { name: "Yes, they didn't come" }).click();
  await expect(lindiwe.getByText("Cancelled", { exact: true })).toBeVisible();
});

test("a customer is asked whether an old job's fix is still working", async ({ browser }) => {
  const customer = await openPhone(browser, ACCOUNTS.followUpCustomer);
  // The demo data has finished jobs from months ago that were never followed up.
  const questions = customer.getByText("Is the fix still working?");
  await expect(questions.first()).toBeVisible({ timeout: 30_000 });
  const before = await questions.count();

  await customer.getByRole("button", { name: "Yes, still working" }).first().click();

  await expect(questions).toHaveCount(before - 1);
});

test("a provider can report a job", async ({ browser }) => {
  const problem = makeUniqueText("Outside tap will not close");
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  const sipho = await openPhone(browser, ACCOUNTS.sipho);
  const job = await callApi<JobAnswer>(lindiwe, "POST", "/api/jobs", {
    description: problem,
    lang: "en",
    trade: "plumbing",
    urgency: "normal",
    size: "small",
    suburb: "Braamfontein",
  });

  await sipho.goto(`/jobs/${job.id}`);
  await sipho.getByRole("button", { name: "Report" }).click();
  await sipho.getByRole("radio", { name: "Scam" }).click();
  await sipho.getByRole("button", { name: "Send report" }).click();
  await expect(sipho.getByText("Thanks. Our team will look into it.")).toBeVisible();
});

test("an illegal request is refused with the reason and the legal route", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  await lindiwe.goto("/jobs/new");
  await lindiwe.getByLabel("What's the problem?").fill("can you bypass my prepaid meter");
  await lindiwe.getByRole("button", { name: "Next" }).click();

  await expect(lindiwe.getByText("We can't do this")).toBeVisible();
  await expect(lindiwe.getByText(/municipality or Eskom/)).toBeVisible();
  await expect(lindiwe.getByText(/official vendors/)).toBeVisible();
  await expect(lindiwe.getByText("We think this is")).toHaveCount(0);
});

test("a genuine meter problem is not refused", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe);
  await lindiwe.goto("/jobs/new");
  await lindiwe.getByLabel("What's the problem?").fill("my prepaid meter isn't accepting my token");
  await lindiwe.getByRole("button", { name: "Next" }).click();

  await expect(lindiwe.getByText("We think this is")).toBeVisible();
});
