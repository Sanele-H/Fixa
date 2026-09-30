// The browser's "install this app" offer. It arrives once per page load as a
// beforeinstallprompt event, usually early, before the screens that show the install card
// have loaded. So we start listening when the app starts, keep the event, and let the card
// read it whenever it mounts (and again each time the person comes back to that screen).

/** The event Chrome and other Chromium browsers fire; it's not in the DOM types yet. */
export interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let savedInstallPrompt: BeforeInstallPromptEvent | null = null;
const changeListeners = new Set<() => void>();

/** Tells every subscribed card that the saved offer appeared or went away. */
function notifyChangeListeners() {
  changeListeners.forEach((listener) => listener());
}

/** Keeps the browser's offer for later, and stops the browser showing its own mini bar. */
function saveInstallPrompt(event: Event) {
  event.preventDefault();
  savedInstallPrompt = event as BeforeInstallPromptEvent;
  notifyChangeListeners();
}

/** Forgets the offer: it was used (it only works once) or the app got installed. */
function clearInstallPrompt() {
  savedInstallPrompt = null;
  notifyChangeListeners();
}

/** Starts catching the offer. Call once, before the first render. */
export function listenForInstallPrompt() {
  window.addEventListener("beforeinstallprompt", saveInstallPrompt);
  window.addEventListener("appinstalled", clearInstallPrompt);
}

/** For useSyncExternalStore: calls `listener` whenever the saved offer changes. Returns the unsubscribe. */
export function subscribeToInstallPrompt(listener: () => void) {
  changeListeners.add(listener);
  return () => {
    changeListeners.delete(listener);
  };
}

/** The saved offer, or null when the browser hasn't made one (or it was already used). */
export function getInstallPrompt() {
  return savedInstallPrompt;
}

/**
 * Opens the browser's install dialog. The offer can only be used once, so it's forgotten
 * straight away whatever the person chooses. Resolves true when they installed.
 */
export async function showInstallPrompt(): Promise<boolean> {
  const installPrompt = savedInstallPrompt;
  if (!installPrompt) {
    return false;
  }
  clearInstallPrompt();
  await installPrompt.prompt();
  const { outcome } = await installPrompt.userChoice;
  return outcome === "accepted";
}
