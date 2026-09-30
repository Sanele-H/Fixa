// Sharing with the phone's own share sheet (WhatsApp, SMS, email), with a fallback where the
// browser can't: a file downloads, and a link is copied.

/** What happened, so the screen can say "Link copied" when there was no share sheet. */
export type ShareOutcome = "shared" | "downloaded" | "copied" | "cancelled";

const SHARE_CANCELLED_ERROR = "AbortError";

/** True when the person closed the share sheet without sharing, which isn't a failure. */
function isShareCancelled(error: unknown) {
  return error instanceof DOMException && error.name === SHARE_CANCELLED_ERROR;
}

/** Saves a file through a temporary link, for browsers that can't share files. */
function downloadFile(file: File) {
  const fileUrl = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = file.name;
  link.click();
  // The click starts the download straight away, but some browsers read the URL a moment later.
  setTimeout(() => URL.revokeObjectURL(fileUrl), 1_000);
}

/** Opens the share sheet with the file itself where the phone supports it, else downloads it. */
export async function shareFile(file: File, title: string): Promise<ShareOutcome> {
  if (!navigator.canShare?.({ files: [file] })) {
    downloadFile(file);
    return "downloaded";
  }
  try {
    await navigator.share({ files: [file], title });
    return "shared";
  } catch (error) {
    if (isShareCancelled(error)) {
      return "cancelled";
    }
    downloadFile(file);
    return "downloaded";
  }
}

/** Opens the share sheet with a link, or copies it where there's no share sheet. */
export async function shareLink(url: string, title: string): Promise<ShareOutcome> {
  if (!navigator.share) {
    await navigator.clipboard.writeText(url);
    return "copied";
  }
  try {
    await navigator.share({ url, title });
    return "shared";
  } catch (error) {
    if (isShareCancelled(error)) {
      return "cancelled";
    }
    await navigator.clipboard.writeText(url);
    return "copied";
  }
}
