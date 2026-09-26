import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { IconLink } from "./Button";

type ScreenProps = {
  /** Leaves room at the bottom for the floating tab bar. */
  hasNav?: boolean;
  children: ReactNode;
};

/** The padded column every screen sits in. */
export function Screen({ hasNav, children }: ScreenProps) {
  return <main className={hasNav ? "screen screen--with-nav" : "screen"}>{children}</main>;
}

/** The round Fixa logo shown top-left on screens with no back button. */
export function AppMark() {
  return (
    <span className="app-mark" aria-hidden="true">
      f
    </span>
  );
}

type ScreenHeaderProps = {
  title: ReactNode;
  eyebrow?: ReactNode;
  subtitle?: ReactNode;
  /**
   * Where the back arrow goes. A path, not history.back(): screens are opened from shared
   * links (WhatsApp), and going back in history would leave the app. Omit it to show the logo.
   */
  backTo?: string;
  /** Round icon buttons for the top-right corner. */
  actions?: ReactNode;
  /** Replaces the logo on the left, for example with an avatar. */
  leading?: ReactNode;
};

/**
 * The top of a screen: a bar with back arrow (or logo) and actions, then a large title.
 * Mirrors the design's header: small round buttons above a big, light heading.
 */
export function ScreenHeader({ title, eyebrow, subtitle, backTo, actions, leading }: ScreenHeaderProps) {
  const { t } = useTranslation();
  const start = backTo ? <IconLink to={backTo} icon="arrowLeft" label={t("nav.back")} /> : (leading ?? <AppMark />);

  return (
    <header className="screen-header">
      <div className="screen-header__bar">
        {start}
        {actions && <div className="screen-header__actions">{actions}</div>}
      </div>
      <div>
        {eyebrow && <p className="screen-header__eyebrow">{eyebrow}</p>}
        <h1 className="screen-header__title">{title}</h1>
        {subtitle && <p className="screen-header__subtitle">{subtitle}</p>}
      </div>
    </header>
  );
}
