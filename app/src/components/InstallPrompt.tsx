import { useState, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";
import { getInstallPrompt, showInstallPrompt, subscribeToInstallPrompt } from "../installPrompt";
import { Button, Card, Icon, IconButton } from "../ui";

const INSTALL_DISMISSED_KEY = "fixa.installPromptDismissed";
const INSTALL_DISMISSED_VALUE = "true";

/** True when the person closed the card on this phone before. Blocked storage means no. */
function getStoredDismissal(): boolean {
  try {
    return localStorage.getItem(INSTALL_DISMISSED_KEY) === INSTALL_DISMISSED_VALUE;
  } catch {
    return false;
  }
}

/** Remembers that the person closed the card, so it stays closed next time. */
function createStoredDismissal(): void {
  try {
    localStorage.setItem(INSTALL_DISMISSED_KEY, INSTALL_DISMISSED_VALUE);
  } catch {
    // Fails quietly if storage is blocked
  }
}

/** True when Fixa is already running as an installed app (Android, or iOS home screen). */
function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((navigator as unknown as { standalone?: boolean }).standalone)
  );
}

/**
 * A small dismissible card prompting the user to install Fixa on their home screen.
 * Shows on HomeScreen and FeedScreen once the browser has offered an install (caught at app
 * start in installPrompt.ts), until it's installed or the person closes the card.
 */
export function InstallPromptCard() {
  const { t } = useTranslation();
  const installPrompt = useSyncExternalStore(subscribeToInstallPrompt, getInstallPrompt);
  const [isDismissed, setIsDismissed] = useState(getStoredDismissal);

  if (isDismissed || !installPrompt || isStandalone()) {
    return null;
  }

  /** Remembers the choice and hides the card. */
  function dismissCard() {
    createStoredDismissal();
    setIsDismissed(true);
  }

  return (
    <Card tone="lavender">
      <div className="row row--between">
        <div className="row">
          <Icon name="download" sizePx={18} />
          <p className="section-title">{t("install.title")}</p>
        </div>
        <IconButton icon="close" label={t("install.dismiss")} isSmall onClick={dismissCard} />
      </div>
      <p className="small muted">{t("install.body")}</p>
      <div>
        <Button variant="primary" isSmall icon="download" onClick={showInstallPrompt}>
          {t("install.button")}
        </Button>
      </div>
    </Card>
  );
}
