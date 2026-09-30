// The frames screens sit in: the phone-width column, the login guard, the tab bar, the
// loading state, and the redirect from "/".

import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, ScrollRestoration } from "react-router";
import type { Role } from "../api/types";
import { getStoredLanguage } from "../i18n";
import { useCurrentUser, useSession } from "../session/SessionContext";
import { Banner, BottomNav, Button, Screen, type NavItem } from "../ui";
import { getHomePath, PATHS } from "./paths";

/** The phone-width column every screen renders in, centred on wider screens. */
export function AppFrame() {
  return (
    <div className="app-frame">
      <Outlet />
      <ScrollRestoration />
    </div>
  );
}

/** Builds the tab bar for a role: customers get Home / New job / Me, providers get Jobs / Record / Me. */
function buildNavItems(role: Role, t: TFunction): NavItem[] {
  const meItem: NavItem = { to: PATHS.me, icon: "user", label: t("nav.me") };
  if (role === "provider") {
    return [
      { to: PATHS.feed, icon: "briefcase", label: t("nav.feed") },
      { to: PATHS.myRecord, icon: "file", label: t("nav.record") },
      meItem,
    ];
  }
  return [
    { to: PATHS.home, icon: "home", label: t("nav.home") },
    { to: PATHS.newJob, icon: "plus", label: t("nav.newJob") },
    meItem,
  ];
}

/** Layout for the main tabs: the screen, with the floating round-button tab bar over it. */
export function TabLayout() {
  const { t } = useTranslation();
  const { role } = useCurrentUser();
  return (
    <>
      <Outlet />
      <BottomNav label={t("nav.label")} items={buildNavItems(role, t)} />
    </>
  );
}

/** Shown while the first screen's code downloads, and while a saved login is checked. */
export function ScreenLoading() {
  const { t } = useTranslation();
  return (
    <Screen>
      <p className="muted" aria-busy="true">
        {t("app.loading")}
      </p>
    </Screen>
  );
}

/** Shown when a saved login couldn't be checked because the server didn't answer. */
function SessionCheckFailed() {
  const { t } = useTranslation();
  const { retryTokenCheck } = useSession();
  return (
    <Screen>
      <Banner tone="warning" title={t("errors.offline")} />
      <Button isBlock onClick={retryTokenCheck}>
        {t("errors.tryAgain")}
      </Button>
    </Screen>
  );
}

/**
 * What shows while there's no user: the loading screen while a saved login is checked, a retry
 * screen if the server didn't answer, and otherwise the login screen.
 */
function NoUserYet() {
  const { isCheckingToken, hasTokenCheckFailed } = useSession();
  if (isCheckingToken) {
    return <ScreenLoading />;
  }
  if (hasTokenCheckFailed) {
    return <SessionCheckFailed />;
  }
  return <Navigate to={PATHS.login} replace />;
}

/**
 * Guards every screen that needs a login, so those screens can call useCurrentUser().
 * Logging out lands here too: the user goes, and this sends the person to /login.
 */
export function RequireSession() {
  const { user } = useSession();
  return user ? <Outlet /> : <NoUserYet />;
}

/** "/" sends people to the language picker the first time, then to login, then to their home tab. */
export function StartRedirect() {
  const { user } = useSession();
  if (!getStoredLanguage()) {
    return <Navigate to={PATHS.welcome} replace />;
  }
  return user ? <Navigate to={getHomePath(user.role)} replace /> : <NoUserYet />;
}
