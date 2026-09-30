// Chat between a job's customer and one provider. Messages arrive as they were written. When
// one comes in another language, the reader is asked, in their own language, whether to
// translate it; once they say yes, the whole chat is translated, and that's remembered for this
// chat on this phone. The server hides contact details until the job is confirmed, adds scam
// warnings in the reader's language, and the list checks for new messages every 3 seconds.

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams, useSearchParams } from "react-router";
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

type MessageListProps = {
  jobId: string;
  providerId: string | undefined;
};

/** The thread, oldest first, scrolled to the newest message, with the translate prompt. */
function MessageList({ jobId, providerId }: MessageListProps) {
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
  }, [thread.length]);

  if (messages.isPending) {
    return <LoadingNote />;
  }
  if (messages.isError) {
    return <LoadError error={messages.error} onRetry={() => messages.refetch()} />;
  }
  if (thread.length === 0) {
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
      <div ref={endRef} />
    </>
  );
}

/** The box at the bottom. Clears once the message is sent; a refused message shows why. */
function Composer({ jobId, providerId }: MessageListProps) {
  const { t } = useTranslation();
  const sendMessage = useSendMessage(jobId);
  const [text, setText] = useState("");

  /** Sends the message, to the provider this thread is with when a customer writes. */
  function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sendMessage.mutate({ text: text.trim(), provider_id: providerId }, { onSuccess: () => setText("") });
  }

  return (
    <>
      {sendMessage.isError && (
        <div className="screen">
          <ErrorBanner error={sendMessage.error} />
        </div>
      )}
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
          onChange={(event) => setText(event.target.value)}
        />
        <IconButton
          type="submit"
          icon="send"
          label={t("chat.send")}
          isInverse
          disabled={sendMessage.isPending || !text.trim()}
        />
      </form>
    </>
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

  if (me.role === "customer" && !providerId) {
    return <PickThread jobId={jobId} />;
  }
  // "Provider" stands in for the name until the profile has loaded, so the title is never blank.
  const otherPersonName = me.role === "customer" ? (provider.data?.display_name ?? t("role.provider")) : t("role.customer");

  return (
    <main className="chat">
      <div className="screen">
        <ScreenHeader backTo={generatePath(PATHS.job, { jobId })} eyebrow={t("chat.eyebrow")} title={otherPersonName} />
        <Banner tone="info" title={t("chat.privacyNote")} />
      </div>

      <section className="chat__messages" aria-live="polite" aria-label={t("chat.messages")}>
        <MessageList jobId={jobId} providerId={providerId} />
      </section>

      <Composer jobId={jobId} providerId={providerId} />
    </main>
  );
}
