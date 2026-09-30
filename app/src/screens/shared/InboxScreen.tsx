// The inbox behind the bell: new quotes, confirmed jobs, messages, check-ins and safety alerts,
// newest first and already in the reader's language. Tapping one opens its job. At the top, a
// way to get the same notifications on the phone's lock screen.

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useNavigate } from "react-router";
import {
  canUsePush,
  isPushOn,
  turnOnPush,
  useInbox,
  useMarkAllRead,
  useMarkRead,
  type InboxItem,
  type PushOutcome,
} from "../../api/notifications";
import { getHomePath, PATHS } from "../../app/paths";
import { ErrorBanner } from "../../components/ErrorBanner";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { formatDateTime } from "../../format";
import { useCurrentUser } from "../../session/SessionContext";
import { Banner, Button, Card, Screen, ScreenHeader } from "../../ui";

const PUSH_OUTCOME_KEYS: Record<Exclude<PushOutcome, "on">, string> = {
  denied: "inbox.pushDenied",
  unavailable: "inbox.pushUnavailable",
  not_set_up: "inbox.pushNotSetUp",
};

/** "Turn on notifications", or a note saying they're on, blocked or not possible here. */
function PushCard() {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<PushOutcome | null>(canUsePush() ? null : "unavailable");
  const [error, setError] = useState<unknown>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    isPushOn()
      .then((isOn) => isOn && setOutcome("on"))
      .catch(() => undefined);
  }, []);

  async function turnOn() {
    setIsBusy(true);
    setError(null);
    try {
      setOutcome(await turnOnPush());
    } catch (problem) {
      setError(problem);
    } finally {
      setIsBusy(false);
    }
  }

  if (outcome === "on") {
    return <Banner tone="info" title={t("inbox.pushOn")} />;
  }
  return (
    <Card tone="lime">
      <p className="section-title">{t("inbox.pushTitle")}</p>
      <p className="small">{t("inbox.pushBody")}</p>
      {outcome && <Banner tone="warning" title={t(PUSH_OUTCOME_KEYS[outcome])} />}
      {error !== null && <ErrorBanner error={error} />}
      {outcome !== "unavailable" && outcome !== "not_set_up" && (
        <Button isBlock icon="bell" onClick={turnOn} disabled={isBusy}>
          {t("inbox.pushTurnOn")}
        </Button>
      )}
    </Card>
  );
}

/** One item: bold while unread; opens its job (or stays here if it has none). */
function InboxRow({ item }: { item: InboxItem }) {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const markRead = useMarkRead();

  function open() {
    if (!item.read) {
      markRead.mutate(item.id);
    }
    if (item.job_id) {
      navigate(generatePath(PATHS.job, { jobId: item.job_id }));
    }
  }

  return (
    <li>
      <button type="button" className={item.read ? "inbox-row" : "inbox-row inbox-row--unread"} onClick={open}>
        <span className="inbox-row__title">{item.title}</span>
        <span className="small">{item.body}</span>
        <span className="small muted">{formatDateTime(item.created_at, i18n.language)}</span>
      </button>
    </li>
  );
}

function InboxList() {
  const { t } = useTranslation();
  const inbox = useInbox();
  const markAllRead = useMarkAllRead();

  if (inbox.isPending) {
    return <LoadingNote />;
  }
  if (inbox.isError) {
    return <LoadError error={inbox.error} onRetry={() => inbox.refetch()} />;
  }
  if (inbox.data.items.length === 0) {
    return <EmptyNote title={t("inbox.emptyTitle")}>{t("inbox.emptyBody")}</EmptyNote>;
  }
  return (
    <section className="stack">
      {inbox.data.unread > 0 && (
        <div className="row row--between">
          <p className="small">{t("inbox.unreadCount", { count: inbox.data.unread })}</p>
          <Button variant="secondary" isSmall onClick={() => markAllRead.mutate()} disabled={markAllRead.isPending}>
            {t("inbox.markAllRead")}
          </Button>
        </div>
      )}
      <ul className="stack moment-list">
        {inbox.data.items.map((item) => (
          <InboxRow key={item.id} item={item} />
        ))}
      </ul>
    </section>
  );
}

export default function InboxScreen() {
  const { t } = useTranslation();
  const { role } = useCurrentUser();

  return (
    <Screen>
      <ScreenHeader backTo={getHomePath(role)} title={t("inbox.title")} />
      <PushCard />
      <InboxList />
    </Screen>
  );
}
