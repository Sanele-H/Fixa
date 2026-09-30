import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button, Card, Icon, IconButton } from "../ui";

const INSTALL_DISMISSED_KEY = "fixa.installPromptDismissed";

function isDismissed(): boolean {
  try {
    return localStorage.getItem(INSTALL_DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

function setDismissed(): void {
  try {
    localStorage.setItem(INSTALL_DISMISSED_KEY, "true");
  } catch {
    // Fails quietly if storage is blocked
  }
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((navigator as unknown as { standalone?: boolean }).standalone)
  );
}

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/**
 * A small dismissible card prompting the user to install Fixa on their home screen.
 * Shows on HomeScreen and FeedScreen when the browser triggers `beforeinstallprompt`.
 */
export function InstallPromptCard() {
  const { t } = useTranslation();
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissedState] = useState<boolean>(isDismissed);
  const [installed, setInstalled] = useState<boolean>(isStandalone);

  useEffect(() => {
    if (installed || dismissed) return;

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    const handleAppInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, [installed, dismissed]);

  if (installed || dismissed || !deferredPrompt) {
    return null;
  }

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    if (outcome === "accepted") {
      setInstalled(true);
    }
  };

  const handleDismiss = () => {
    setDismissed();
    setDismissedState(true);
  };

  return (
    <Card tone="lavender" className="install-prompt-card">
      <div className="row row--between row--align-start">
        <div className="stack stack--small" style={{ flex: 1, paddingRight: "var(--space-2, 8px)" }}>
          <div className="row row--align-center" style={{ gap: "6px" }}>
            <Icon name="download" sizePx={18} />
            <h3 className="section-title" style={{ margin: 0, fontSize: "1rem" }}>
              {t("install.title")}
            </h3>
          </div>
          <p className="muted" style={{ margin: 0, fontSize: "0.875rem" }}>
            {t("install.body")}
          </p>
        </div>
        <IconButton icon="ban" label={t("install.dismiss")} isSmall onClick={handleDismiss} />
      </div>
      <div style={{ marginTop: "var(--space-2, 12px)" }}>
        <Button variant="primary" isSmall icon="download" onClick={handleInstallClick}>
          {t("install.button")}
        </Button>
      </div>
    </Card>
  );
}
