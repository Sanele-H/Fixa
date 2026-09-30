// Chat across languages: messages arrive as written with a prompt to translate, the choice is
// remembered, and a phone number never gets through before the job is confirmed.

import { expect, test } from "@playwright/test";
import { ACCOUNTS, callApi, getAppText, openPhone } from "./helpers";

const ZULU_TEXT = "Ngingafika ngoLwesibili ekuseni, ngiphethe amathuluzi.";
const PHONE_NUMBER = "082 123 4567";

test("the translate prompt works both ways and contact details stay hidden", async ({ browser }) => {
  const lindiwe = await openPhone(browser, ACCOUNTS.lindiwe, "en");
  const sipho = await openPhone(browser, ACCOUNTS.sipho, "zu");
  const job = await callApi<{ id: string }>(lindiwe, "POST", "/api/jobs", {
    description: "My geyser is leaking",
    lang: "en",
    trade: "plumbing",
    urgency: "urgent",
    size: "small",
    suburb: "Braamfontein",
  });
  await callApi(sipho, "POST", `/api/jobs/${job.id}/quotes`, { amount_rands: 450, when: "2026-10-02T08:00:00+02:00" });

  await test.step("Sipho writes in isiZulu and sees it as he wrote it", async () => {
    await sipho.goto(`/jobs/${job.id}/chat`);
    await sipho.getByLabel(getAppText("zu", "chat.placeholder")).fill(ZULU_TEXT);
    await sipho.getByRole("button", { name: getAppText("zu", "chat.send") }).click();
    await expect(sipho.getByText(ZULU_TEXT)).toBeVisible();
  });

  await test.step("Lindiwe gets the original, a prompt in English, and the translation on a tap", async () => {
    await lindiwe.goto(`/jobs/${job.id}`);
    await lindiwe.getByRole("link", { name: "Message" }).click();
    await expect(lindiwe.getByRole("heading", { name: "Sipho" })).toBeVisible();
    await expect(lindiwe.getByText(ZULU_TEXT)).toBeVisible();
    await expect(lindiwe.getByText("This message is in isiZulu.")).toBeVisible();
    await lindiwe.getByRole("button", { name: "Translate to English" }).click();
    await expect(lindiwe.getByRole("button", { name: "See original" })).toBeVisible();
    await expect(lindiwe.locator(".bubble--theirs p").first()).not.toHaveText(ZULU_TEXT);
    await lindiwe.reload();
    await expect(lindiwe.getByRole("button", { name: "See original" })).toBeVisible();
  });

  await test.step("Lindiwe's phone number is hidden, and Sipho can translate her English", async () => {
    await lindiwe.getByLabel("Write a message").fill(`Tuesday morning is great. Call me on ${PHONE_NUMBER}`);
    await lindiwe.getByRole("button", { name: "Send" }).click();
    await expect(sipho.getByText(getAppText("zu", "translation.messageIn", { language: "English" }))).toBeVisible({ timeout: 30_000 });
    await expect(sipho.getByText(PHONE_NUMBER)).toHaveCount(0);
    await expect(sipho.getByText(getAppText("zu", "chat.contactsHidden"), { exact: true })).toBeVisible();
    await sipho.getByRole("button", { name: getAppText("zu", "translation.translateTo", { language: "isiZulu" }) }).click();
    await expect(sipho.locator(".bubble--theirs p").first()).not.toContainText("Tuesday morning is great");
  });
});
