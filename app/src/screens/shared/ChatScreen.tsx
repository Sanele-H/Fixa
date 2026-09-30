// Chat between a job's customer and one provider. Messages arrive as they were written. When
// one comes in another language, the reader is asked, in their own language, whether to
// translate it; once they say yes, the whole chat is translated, and that's remembered for this
// chat on this phone. The server hides contact details until the job is confirmed, adds scam
// warnings in the reader's language, and the list checks for new messages every 3 seconds.

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams, useSearchParams } from "react-router";
import { getErrorCode } from "../../api/errors";
import { useMessages, useSendMessage } from "../../api/chat";
import { ErrorBanner } from "../../components/ErrorBanner";
import { useProviderProfile } from "../../api/providers";
import type { Language, Message } from "../../api/types";
import { CHAT_WITH_PARAM, PATHS } from "../../app/paths";
import { EmptyNote, LoadError, LoadingNote } from "../../components/LoadState";
import { MessageBubble } from "../../components/MessageBubble";
import { useCurrentUser } from "../../session/SessionContext";
import { Banner, ButtonLink, IconButton, Screen, ScreenHeader } from "../../ui";

const TRANSLATE_CHOICE_STORAGE_PREFIX = "fixa.translateChat.";
const TRANSLATE_CHOICE_ON = "on";
const DRAFT_CHAT_STORAGE_PREFIX = "fixa.draft.chat.";

function getChatDraftKey(jobId: string, providerId?: string) {
  return DRAFT_CHAT_STORAGE_PREFIX + jobId + (providerId ? "." + providerId : "");
}

function getStoredChatDraft(jobId: string, providerId?: string): string {
  try {
    return localStorage.getItem(getChatDraftKey(jobId, providerId)) ?? "";
  } catch {
    return "";
  }
}

function updateStoredChatDraft(jobId: string, providerId: string | undefined, text: string) {
  try {
    if (text.trim()) {
      localStorage.setItem(getChatDraftKey(jobId, providerId), text);
    } else {
      localStorage.removeItem(getChatDraftKey(jobId, providerId));
    }
  } catch {
    // Ignore storage failure
  }
}

function clearStoredChatDraft(jobId: string, providerId?: string) {
  try {
    localStorage.removeItem(getChatDraftKey(jobId, providerId));
  } catch {
    // Ignore storage failure
  }
}

/** Whether the reader chose to translate this job's chat on this phone. Blocked storage means no. */
function getStoredTranslateChoice(jobId: string) {
  try {
    return localStorage.getItem(TRANSLATE_CHOICE_STORAGE_PREFIX + jobId) === TRANSLATE_CHOICE_ON;
  } catch {
    return false;
  }
}

/** Remembers that the reader translates this job's chat. Fails quietly if storage is blocked. */
function updateStoredTranslateChoice(jobId: string) {
  try {
    localStorage.setItem(TRANSLATE_CHOICE_STORAGE_PREFIX + jobId, TRANSLATE_CHOICE_ON);
  } catch {
    // The chat is still translated for this visit.
  }
}

/** Whether this chat is translated, starting from the reader's last choice for it. */
function useChatTranslation(jobId: string) {
  const [isTranslating, setIsTranslating] = useState(() => getStoredTranslateChoice(jobId));
  function startTranslating() {
    setIsTranslating(true);
    updateStoredTranslateChoice(jobId);
  }
  return [isTranslating, startTranslating] as const;
}

/** The messages in one thread: a customer's with one provider. A provider only has one thread. */
function selectThread(messages: Message[], providerId: string | undefined) {
  if (!providerId) {
    return messages;
  }
  return messages.filter((message) => message.sender_id === providerId || message.recipient_id === providerId);
}

/** The newest message from the other person in another language: where the translate prompt goes. */
function findTranslatePromptId(messages: Message[], myId: string, appLanguage: Language) {
  const otherLanguageMessages = messages.filter(
    (message) => message.sender_id !== myId && message.original_lang !== appLanguage,
  );
  return otherLanguageMessages.at(-1)?.id;
}

type PendingMessage = {
  tempId: string;
  text: string;
  providerId?: string;
  status: "sending" | "failed";
  error?: unknown;
};

type MessageListProps = {
  jobId: string;
  providerId: string | undefined;
  pendingMessages: PendingMessage[];
  onRetryPending: (msg: PendingMessage) => void;
};

/** The thread, oldest first, scrolled to the newest message, with the translate prompt. */
function MessageList({ jobId, providerId, pendingMessages, onRetryPending }: MessageListProps) {
  const { t, i18n } = useTranslation();
  const me = useCurrentUser();
  const messages = useMessages(jobId);
  const [isTranslating, startTranslating] = useChatTranslation(jobId);
  const endRef = useRef<HTMLDivElement>(null);
  const appLanguage = i18n.language as Language;
  const thread = selectThread(messages.data ?? [], providerId);
  const translatePromptId = isTranslating ? undefined : findTranslatePromptId(thread, me.id, appLanguage);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [thread.length, pendingMessages.length]);

  if (messages.isPending && thread.length === 0 && pendingMessages.length === 0) {
    return <LoadingNote />;
  }
  if (messages.isError && thread.length === 0 && pendingMessages.length === 0) {
    return <LoadError error={messages.error} onRetry={() => messages.refetch()} />;
  }
  if (thread.length === 0 && pendingMessages.length === 0) {
    return <EmptyNote title={t("chat.emptyTitle")}>{t("chat.emptyBody")}</EmptyNote>;
  }
  return (
    <>
      {thread.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          isMine={message.sender_id === me.id}
          appLanguage={appLanguage}
          isTranslating={isTranslating}
          onTranslate={message.id === translatePromptId ? startTranslating : undefined}
        />
      ))}
      {pendingMessages.map((pendingMsg) => (
        <article
          key={pendingMsg.tempId}
          className="bubble bubble--mine"
          style={{
            opacity: pendingMsg.status === "sending" ? 0.7 : 1,
            cursor: pendingMsg.status === "failed" ? "pointer" : "default",
          }}
          onClick={pendingMsg.status === "failed" ? () => onRetryPending(pendingMsg) : undefined}
        >
          <p>{pendingMsg.text}</p>
          <footer className="bubble__meta" style={{ justifyContent: "space-between", alignItems: "center" }}>
            {pendingMsg.status === "sending" ? (
              <span className="muted">{t("app.loading")}</span>
            ) : (
              <span
                style={{
                  background: "var(--color-warning-bg, #fff3cd)",
                  color: "var(--color-warning-text, #856404)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "var(--text-xs)",
                }}
              >
                {t("chat.notSentYet")} • {t("chat.tapToRetry")}
              </span>
            )}
          </footer>
        </article>
      ))}
      <div ref={endRef} />
    </>
  );
}

type ComposerProps = {
  jobId: string;
  providerId: string | undefined;
  onSendText: (text: string) => void;
  isSending: boolean;
};

/** The box at the bottom. Clears once the message is sent; a refused message shows why. */
function Composer({ jobId, providerId, onSendText, isSending }: ComposerProps) {
  const { t } = useTranslation();
  const [text, setText] = useState(() => getStoredChatDraft(jobId, providerId));

  useEffect(() => {
    setText(getStoredChatDraft(jobId, providerId));
  }, [jobId, providerId]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setText(val);
    updateStoredChatDraft(jobId, providerId, val);
  };

  const send = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!text.trim() || isSending) return;
    onSendText(text.trim());
    setText("");
    clearStoredChatDraft(jobId, providerId);
  };

  return (
    <form className="composer" onSubmit={send}>
      <label className="visually-hidden" htmlFor="chat-composer">
        {t("chat.placeholder")}
      </label>
      <input
        id="chat-composer"
        className="composer__input"
        placeholder={t("chat.placeholder")}
        autoComplete="off"
        value={text}
        onChange={handleChange}
      />
      <IconButton
        type="submit"
        icon="send"
        label={t("chat.send")}
        isInverse
        disabled={isSending || !text.trim()}
      />
    </form>
  );
}

/** A customer opened the chat without saying which provider: point them to the quotes. */
function PickThread({ jobId }: { jobId: string }) {
  const { t } = useTranslation();
  return (
    <Screen>
      <ScreenHeader backTo={generatePath(PATHS.job, { jobId })} eyebrow={t("chat.eyebrow")} title={t("chat.pickThreadTitle")} />
      <EmptyNote title={t("chat.pickThreadTitle")}>{t("chat.pickThreadBody")}</EmptyNote>
      <ButtonLink to={generatePath(PATHS.job, { jobId })} isBlock>
        {t("chat.openJob")}
      </ButtonLink>
    </Screen>
  );
}

export default function ChatScreen() {
  const { t } = useTranslation();
  const me = useCurrentUser();
  const { jobId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const providerId = me.role === "customer" ? (searchParams.get(CHAT_WITH_PARAM) ?? undefined) : undefined;
  const provider = useProviderProfile(providerId);

  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([]);
  const [refusalError, setRefusalError] = useState<unknown | null>(null);
  const sendMessage = useSendMessage(jobId);

  const attemptSend = async (msg: PendingMessage) => {
    setPendingMessages((prev) =>
      prev.map((m) => (m.tempId === msg.tempId ? { ...m, status: "sending", error: undefined } : m))
    );
    try {
      await sendMessage.mutateAsync({ text: msg.text, provider_id: msg.providerId });
      setPendingMessages((prev) => prev.filter((m) => m.tempId !== msg.tempId));
    } catch (err) {
      if (getErrorCode(err) === "prohibited_request") {
        setPendingMessages((prev) => prev.filter((m) => m.tempId !== msg.tempId));
        clearStoredChatDraft(jobId, providerId);
        setRefusalError(err);
      } else {
        setPendingMessages((prev) =>
          prev.map((m) => (m.tempId === msg.tempId ? { ...m, status: "failed", error: err } : m))
        );
      }
    }
  };

  useEffect(() => {
    function handleOnline() {
      setPendingMessages((prev) => {
        const failed = prev.filter((m) => m.status === "failed");
        failed.forEach((m) => attemptSend(m));
        return prev;
      });
    }
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, [jobId, providerId]);

  if (me.role === "customer" && !providerId) {
    return <PickThread jobId={jobId} />;
  }
  const otherPersonName = me.role === "customer" ? (provider.data?.display_name ?? t("role.provider")) : t("role.customer");

  const handleSendText = (text: string) => {
    setRefusalError(null);
    clearStoredChatDraft(jobId, providerId);
    const tempId = "pending-" + Date.now() + "-" + Math.random().toString(36).substring(2, 6);
    const newMsg: PendingMessage = { tempId, text, providerId, status: "sending" };
    setPendingMessages((prev) => [...prev, newMsg]);
    attemptSend(newMsg);
  };

  return (
    <main className="chat">
      <div className="screen">
        <ScreenHeader backTo={generatePath(PATHS.job, { jobId })} eyebrow={t("chat.eyebrow")} title={otherPersonName} />
        <Banner tone="info" title={t("chat.privacyNote")} />
        {refusalError != null && <ErrorBanner error={refusalError} />}
      </div>

      <section className="chat__messages" aria-live="polite" aria-label={t("chat.messages")}>
        <MessageList
          jobId={jobId}
          providerId={providerId}
          pendingMessages={pendingMessages}
          onRetryPending={attemptSend}
        />
      </section>

      <Composer
        jobId={jobId}
        providerId={providerId}
        onSendText={handleSendText}
        isSending={sendMessage.isPending}
      />
    </main>
  );
}
