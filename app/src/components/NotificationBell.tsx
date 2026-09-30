// The bell in the home and feed headers: opens the inbox, with the number of unread items on it.

import { useTranslation } from "react-i18next";
import { useInbox } from "../api/notifications";
import { PATHS } from "../app/paths";
import { IconLink } from "../ui";

/** More than this shows as "9+", so the badge stays small. */
const MAX_BADGE_COUNT = 9;

export function NotificationBell() {
  const { t } = useTranslation();
  const inbox = useInbox();
  const unread = inbox.data?.unread ?? 0;
  const label = unread > 0 ? `${t("inbox.title")}, ${t("inbox.unreadCount", { count: unread })}` : t("inbox.title");

  return (
    <span className="icon-badge">
      <IconLink to={PATHS.inbox} icon="bell" label={label} />
      {unread > 0 && (
        <span className="icon-badge__count" aria-hidden="true">
          {unread > MAX_BADGE_COUNT ? `${MAX_BADGE_COUNT}+` : unread}
        </span>
      )}
    </span>
  );
}
