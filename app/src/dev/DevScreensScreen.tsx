// Development only (/dev/screens): every screen in one list, so you can jump around while
// building. Left out of production builds by the router. Its text is dev-only, so not translated.
// Screens behind the login open only once someone is logged in, with that account's tabs.

import { generatePath } from "react-router";
import { PATHS, PROFILE_FROM_NEARBY, PROFILE_FROM_PARAM } from "../app/paths";
import { useSession } from "../session/SessionContext";
import { RowCard, Screen, ScreenHeader } from "../ui";
/** Seeded ids the links open: Lindiwe's job, and Sipho the plumber. Reseed if they're missing. */
const DEMO_JOB_ID = "job_001";
const DEMO_PROVIDER_ID = "prov_002";

const jobParams = { jobId: DEMO_JOB_ID };
const profilePath = generatePath(PATHS.provider, { providerId: DEMO_PROVIDER_ID });

const SCREEN_LINKS = [
  { group: "Start", label: "Language picker", to: PATHS.welcome },
  { group: "Start", label: "Log in", to: PATHS.login },
  { group: "Customer", label: "Home", to: PATHS.home },
  { group: "Customer", label: "Describe a job", to: PATHS.newJob },
  { group: "Customer", label: "Who works near you", to: PATHS.nearby },
  { group: "Customer", label: "Ranked providers", to: generatePath(PATHS.jobProviders, jobParams) },
  { group: "Shared", label: "Job page", to: generatePath(PATHS.job, jobParams) },
  { group: "Shared", label: "Chat", to: generatePath(PATHS.jobChat, jobParams) },
  { group: "Shared", label: "Provider profile", to: profilePath },
  { group: "Shared", label: "Provider profile (from nearby)", to: `${profilePath}?${PROFILE_FROM_PARAM}=${PROFILE_FROM_NEARBY}` },
  { group: "Shared", label: "Me", to: PATHS.me },
  { group: "Provider", label: "Job feed", to: PATHS.feed },
  { group: "Provider", label: "Send a quote", to: generatePath(PATHS.jobQuote, jobParams) },
  { group: "Provider", label: "Verify ID", to: PATHS.verifyId },
  { group: "Provider", label: "Log an off-app job", to: PATHS.offAppJob },
  { group: "Provider", label: "My record", to: PATHS.myRecord },
  { group: "Other", label: "Not found", to: "/nowhere" },
];

export default function DevScreensScreen() {
  const { user } = useSession();
  const loggedInAs = user ? `Logged in as ${user.display_name} (${user.role}).` : "Nobody is logged in.";
  return (
    <Screen>
      <ScreenHeader
        eyebrow="Development only"
        title="All screens"
        subtitle={`${loggedInAs} Customers are 082 000 0001–0080, providers 071 000 0001–0060; log out from Me to switch.`}
      />
      <div className="stack">
        {SCREEN_LINKS.map((link) => (
          <RowCard key={link.to} eyebrow={link.group} title={link.label} to={link.to} tone="raised" />
        ))}
      </div>
    </Screen>
  );
}
