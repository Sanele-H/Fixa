// The route table. Every screen is lazy-loaded, so the first visit only downloads the screen
// it opens (part of the 300 KB first-load budget). Everything except the start screens needs
// a login (RequireSession).

import type { ComponentType } from "react";
import { createBrowserRouter, type RouteObject } from "react-router";
import { AppFrame, RequireSession, ScreenLoading, StartRedirect, TabLayout } from "./layouts";
import { PATHS } from "./paths";

type ScreenModule = { default: ComponentType };

/** Adapts a screen's dynamic import to the router's `lazy` option. */
function loadScreen(importScreen: () => Promise<ScreenModule>) {
  return async () => ({ Component: (await importScreen()).default });
}

/** Screens that show the tab bar. */
const tabRoutes: RouteObject[] = [
  { path: PATHS.home, lazy: loadScreen(() => import("../screens/customer/HomeScreen")) },
  { path: PATHS.feed, lazy: loadScreen(() => import("../screens/provider/FeedScreen")) },
  { path: PATHS.myRecord, lazy: loadScreen(() => import("../screens/provider/MyRecordScreen")) },
  { path: PATHS.me, lazy: loadScreen(() => import("../screens/shared/MeScreen")) },
];

/** The screens before login: the language picker and the login itself. */
const startRoutes: RouteObject[] = [
  { path: PATHS.welcome, lazy: loadScreen(() => import("../screens/start/WelcomeScreen")) },
  { path: PATHS.login, lazy: loadScreen(() => import("../screens/start/LoginScreen")) },
];

/** Focused screens: a back arrow instead of the tab bar. */
const flowRoutes: RouteObject[] = [
  { path: PATHS.newJob, lazy: loadScreen(() => import("../screens/customer/NewJobScreen")) },
  { path: PATHS.nearby, lazy: loadScreen(() => import("../screens/customer/NearbyProvidersScreen")) },
  { path: PATHS.jobProviders, lazy: loadScreen(() => import("../screens/customer/RankedProvidersScreen")) },
  { path: PATHS.job, lazy: loadScreen(() => import("../screens/shared/JobScreen")) },
  { path: PATHS.jobChat, lazy: loadScreen(() => import("../screens/shared/ChatScreen")) },
  { path: PATHS.provider, lazy: loadScreen(() => import("../screens/shared/ProviderProfileScreen")) },
  { path: PATHS.jobQuote, lazy: loadScreen(() => import("../screens/provider/QuoteScreen")) },
  { path: PATHS.verifyId, lazy: loadScreen(() => import("../screens/provider/VerifyIdScreen")) },
  { path: PATHS.offAppJob, lazy: loadScreen(() => import("../screens/provider/OffAppJobScreen")) },
  { path: PATHS.camera, lazy: loadScreen(() => import("../screens/shared/CameraScreen")) },
  { path: PATHS.inbox, lazy: loadScreen(() => import("../screens/shared/InboxScreen")) },
];

/** A page listing every screen, for moving around while building. Left out of production builds. */
const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: PATHS.devScreens, lazy: loadScreen(() => import("../dev/DevScreensScreen")) }]
  : [];

export const router = createBrowserRouter([
  {
    element: <AppFrame />,
    hydrateFallbackElement: <ScreenLoading />,
    children: [
      { path: PATHS.start, element: <StartRedirect /> },
      ...startRoutes,
      {
        element: <RequireSession />,
        children: [{ element: <TabLayout />, children: tabRoutes }, ...flowRoutes],
      },
      ...devRoutes,
      { path: "*", lazy: loadScreen(() => import("../screens/NotFoundScreen")) },
    ],
  },
]);
