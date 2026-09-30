// End-to-end tests: the real app in a real browser, the way people use it, on phone-sized screens.
//
// Local (default): `npm run dev` running and a seeded database, then `npm run test:e2e`.
// Live: set E2E_BASE_URL to the frontend's address, for example
//   PowerShell:  $env:E2E_BASE_URL="https://fixa-2o94.onrender.com"; npm run test:e2e:smoke
//   bash:        E2E_BASE_URL=https://fixa-2o94.onrender.com npm run test:e2e:smoke
// The @smoke tests change nothing. The rest post jobs, quotes and chats, so reseed afterwards.

import { defineConfig } from "@playwright/test";
import { BASE_URL, IS_LIVE } from "./helpers";

/** Render's free services sleep, and the first request after that can take a minute. */
const LIVE_TEST_TIMEOUT_MS = 180_000;
const LOCAL_TEST_TIMEOUT_MS = 60_000;

export default defineConfig({
  testDir: ".",
  // Every test uses the same database and demo accounts, so they run one at a time.
  workers: 1,
  fullyParallel: false,
  timeout: IS_LIVE ? LIVE_TEST_TIMEOUT_MS : LOCAL_TEST_TIMEOUT_MS,
  expect: { timeout: IS_LIVE ? 30_000 : 10_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "report" }]],
  outputDir: "results",
  globalSetup: "./global-setup.ts",
  use: {
    baseURL: BASE_URL,
    // The browser already on the laptop, so nothing needs downloading: Edge on Windows, Chrome
    // elsewhere. E2E_BROWSER=chrome (or msedge) picks one.
    channel: process.env.E2E_BROWSER ?? (process.platform === "win32" ? "msedge" : "chrome"),
    viewport: { width: 390, height: 844 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
