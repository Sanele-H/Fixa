// Before any test: wait for the app and the API to answer (a sleeping Render service can take a
// minute), and check a demo account can log in. Fails early, with what to fix, instead of every
// test timing out.

import { ACCOUNTS, BASE_URL, DEMO_OTP, IS_LIVE } from "./helpers";

const WAKE_UP_LIMIT_MS = 120_000;
const RETRY_PAUSE_MS = 3_000;

/** Waits until GET /api/health on the app's address answers 200, or gives up with a reason. */
async function waitForApi() {
  const deadline = Date.now() + WAKE_UP_LIMIT_MS;
  let lastProblem = "";
  while (Date.now() < deadline) {
    try {
      const answer = await fetch(`${BASE_URL}/api/health`);
      if (answer.ok && answer.headers.get("content-type")?.includes("json")) {
        return;
      }
      lastProblem = `GET /api/health answered ${answer.status} ${answer.headers.get("content-type")}`;
    } catch (error) {
      lastProblem = String(error);
    }
    await new Promise((resolve) => setTimeout(resolve, RETRY_PAUSE_MS));
  }
  const hint = IS_LIVE
    ? "On Render, the frontend needs rewrites sending /api/*, /record/* and /verify/* to the API, then /* to /index.html."
    : "Start the app with `npm run dev`.";
  throw new Error(`The API isn't reachable at ${BASE_URL}/api (${lastProblem}). ${hint}`);
}

/** Checks the demo login works, which needs a seeded database and the right DEMO_OTP. */
async function checkDemoLogin() {
  const answer = await fetch(`${BASE_URL}/api/auth/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone: ACCOUNTS.lindiwe, otp: DEMO_OTP }),
  });
  if (!answer.ok) {
    throw new Error(
      `Demo login failed (${answer.status}). Seed the database (node scripts/run-python.mjs -m fixa_api.seed, ` +
        "with DATABASE_URL set to the database being tested), and check DEMO_OTP matches E2E_OTP (default 123456).",
    );
  }
}

export default async function globalSetup() {
  await waitForApi();
  await checkDemoLogin();
}
