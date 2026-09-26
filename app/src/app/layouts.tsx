// The frames screens sit in: the phone-width column, the tab bar, the loading state,
// and the redirect from "/".

import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, ScrollRestoration } from "react-router";
import type { Role } from "../api/types";
import { getStoredLanguage } from "../i18n";
import { useSession } from "../session/SessionContext";
import { BottomNav, Screen, type NavItem } from "../ui";
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
  const { role } = useSession();
  return (
    <>
      <Outlet />
      <BottomNav label={t("nav.label")} items={buildNavItems(role, t)} />
    </>
  );
}

/** Shown while the first screen's code downloads. */
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

/**
 * "/" sends people to the language picker the first time, and to their home tab after that.
 * P1: once login works, send people with no session to /login instead of home.
 */
export function StartRedirect() {
  const { role } = useSession();
  const targetPath = getStoredLanguage() ? getHomePath(role) : PATHS.welcome;
  return <Navigate to={targetPath} replace />;
}
