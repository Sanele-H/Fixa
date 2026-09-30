// Chat between a job's customer and one provider. Messages arrive as they were written. When
// one comes in another language, the reader is asked, in their own language, whether to
// translate it; once they say yes, the whole chat is translated, and that's remembered for this
// chat on this phone. The server hides contact details until the job is confirmed, adds scam
// warnings in the reader's language, and the list checks for new messages every 3 seconds.

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams, useSearchParams } from "react-router";
import { getErrorCode, isRetryableError, REFUSAL_ERROR_CODES } from "../../api/errors";
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

/** Where a thread's unsent text is kept: one per job, and per provider for a customer. */
function getChatDraftKey(jobId: string, providerId?: string) {
  return DRAFT_CHAT_STORAGE_PREFIX + jobId + (providerId ? "." + providerId : "");
}

/** The thread's unsent text from last time, or "" (also when storage is blocked). */
function getStoredChatDraft(jobId: string, providerId?: string): string {
  try {
    return localStorage.getItem(getChatDraftKey(jobId, providerId)) ?? "";
  } catch {
    return "";
  }
}

/** Keeps the thread's unsent text; blank text removes the draft. Fails quietly if storage is blocked. */
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

/** A message I sent that the server hasn't got yet: on its way, or waiting to be retried. */
type PendingMessage = {
  pendingId: string;
  text: string;
  /** The provider this thread is with, when a customer writes. */
  providerId?: string;
  status: "sending" | "failed";
};

let pendingMessageCount = 0;

/** A key for a pending message, unique on this page. */
function createPendingId() {
  pendingMessageCount += 1;
  return `pending-${pendingMessageCount}`;
}

/** A message of mine the server hasn't got yet: faded while sending, with a retry button once it failed. */
function PendingBubble({ pendingMessage, onRetry }: { pendingMessage: PendingMessage; onRetry: (pendingMessage: PendingMessage) => void }) {
  const { t } = useTranslation();
  const isSending = pendingMessage.status === "sending";
  return (
    <article className={isSending ? "bubble bubble--mine bubble--pending" : "bubble bubble--mine"}>
      <p>{pendingMessage.text}</p>
      <footer className="bubble__meta">
        {isSending ? (
          <span>{t("app.loading")}</span>
        ) : (
          <button type="button" className="chip chip--warning bubble__retry" onClick={() => onRetry(pendingMessage)}>
            {t("chat.notSentYet")} · {t("chat.tapToRetry")}
          </button>
        )}
      </footer>
    </article>
  );
}

type MessageListProps = {
  jobId: string;
  providerId: string | undefined;
  /** Only this thread's pending messages. */
  pendingMessages: PendingMessage[];
  onRetryPending: (pendingMessage: PendingMessage) => void;
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
      {pendingMessages.map((pendingMessage) => (
        <PendingBubble key={pendingMessage.pendingId} pendingMessage={pendingMessage} onRetry={onRetryPending} />
      ))}
      <div ref={endRef} />
    </>
  );
}

type ComposerProps = {
  text: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  isSending: boolean;
};

/** The box at the bottom. The screen owns its text, so a failed message can be put back in it. */
function Composer({ text, onChangeText, onSend, isSending }: ComposerProps) {
  const { t } = useTranslation();

  /** Sends what's typed, unless the box is empty or a message is still on its way. */
  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (text.trim() && !isSending) {
      onSend();
    }
  }

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
        onChange={(event) => onChangeText(event.target.value)}
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

  const [draftText, setDraftText] = useState(() => getStoredChatDraft(jobId, providerId));
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([]);
  const [sendError, setSendError] = useState<unknown>(null);
  const sendMessage = useSendMessage(jobId);

  // Each thread keeps its own draft: load it when the customer switches to another provider.
  useEffect(() => {
    setDraftText(getStoredChatDraft(jobId, providerId));
  }, [jobId, providerId]);

  /** Changes the text in the box and keeps it as this thread's draft. */
  function updateDraft(text: string) {
    setDraftText(text);
    updateStoredChatDraft(jobId, providerId, text);
  }

  /**
   * Puts an unsent message's text back in the box, so nothing typed is lost. Leaves the box
   * alone when the person has already started typing something new.
   */
  function restoreDraft(pendingMessage: PendingMessage) {
    setDraftText((currentText) => (currentText.trim() ? currentText : pendingMessage.text));
    if (!getStoredChatDraft(jobId, pendingMessage.providerId).trim()) {
      updateStoredChatDraft(jobId, pendingMessage.providerId, pendingMessage.text);
    }
  }

  /** Marks a pending message as on its way, or as waiting for a retry. */
  function updatePendingStatus(pendingId: string, status: PendingMessage["status"]) {
    setPendingMessages((current) =>
      current.map((pendingMessage) => (pendingMessage.pendingId === pendingId ? { ...pendingMessage, status } : pendingMessage)),
    );
  }

  /** Takes a message off the pending list: the server has it, or it can't be sent. */
  function deletePendingMessage(pendingId: string) {
    setPendingMessages((current) => current.filter((pendingMessage) => pendingMessage.pendingId !== pendingId));
  }

  /**
   * Sends a pending message; it leaves the list once the server has it (the thread then shows
   * the real one). When trying again could help (no connection, or a server error) it stays
   * as "Not sent yet" to retry. Otherwise it's dropped and the reason shown, and its text goes
   * back in the box, except when the server refused the content itself (a prohibited request
   * or a restricted account), which must not be sent again.
   */
  async function attemptSend(pendingMessage: PendingMessage) {
    updatePendingStatus(pendingMessage.pendingId, "sending");
    try {
      await sendMessage.mutateAsync({ text: pendingMessage.text, provider_id: pendingMessage.providerId });
      deletePendingMessage(pendingMessage.pendingId);
    } catch (error) {
      if (isRetryableError(error)) {
        updatePendingStatus(pendingMessage.pendingId, "failed");
        return;
      }
      deletePendingMessage(pendingMessage.pendingId);
      setSendError(error);
      if (!REFUSAL_ERROR_CODES.includes(getErrorCode(error) ?? "")) {
        restoreDraft(pendingMessage);
      }
    }
  }

  // When the phone gets its connection back, retry every message that couldn't be sent. No
  // dependency list: re-subscribing each render is cheap, and the handler always sees the
  // latest pending list.
  useEffect(() => {
    function retryFailedMessages() {
      pendingMessages
        .filter((pendingMessage) => pendingMessage.status === "failed")
        .forEach((pendingMessage) => attemptSend(pendingMessage));
    }
    window.addEventListener("online", retryFailedMessages);
    return () => window.removeEventListener("online", retryFailedMessages);
  });

  if (me.role === "customer" && !providerId) {
    return <PickThread jobId={jobId} />;
  }
  const otherPersonName = me.role === "customer" ? (provider.data?.display_name ?? t("role.provider")) : t("role.customer");
  const threadPendingMessages = pendingMessages.filter((pendingMessage) => pendingMessage.providerId === providerId);

  /** Empties the box and sends what was in it, showing it as pending until the server has it. */
  function sendDraft() {
    const pendingMessage: PendingMessage = {
      pendingId: createPendingId(),
      text: draftText.trim(),
      providerId,
      status: "sending",
    };
    setSendError(null);
    updateDraft("");
    setPendingMessages((current) => [...current, pendingMessage]);
    attemptSend(pendingMessage);
  }

  return (
    <main className="chat">
      <div className="screen">
        <ScreenHeader backTo={generatePath(PATHS.job, { jobId })} eyebrow={t("chat.eyebrow")} title={otherPersonName} />
        <Banner tone="info" title={t("chat.privacyNote")} />
        {sendError != null && <ErrorBanner error={sendError} />}
      </div>

      <section className="chat__messages" aria-live="polite" aria-label={t("chat.messages")}>
        <MessageList
          jobId={jobId}
          providerId={providerId}
          pendingMessages={threadPendingMessages}
          onRetryPending={attemptSend}
        />
      </section>

      <Composer text={draftText} onChangeText={updateDraft} onSend={sendDraft} isSending={sendMessage.isPending} />
    </main>
  );
}
