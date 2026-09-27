import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Message } from "../api/types";
import { formatTime } from "../format";
import { Banner, Icon } from "../ui";

type MessageBubbleProps = {
  message: Message;
  isMine: boolean;
};

/**
 * One chat message, already translated into the reader's language by the server.
 * "See original" flips to the sender's own words. Hidden contact details, translation
 * doubts and scam warnings each get their own marker under the text.
 */
export function MessageBubble({ message, isMine }: MessageBubbleProps) {
  const { t, i18n } = useTranslation();
  const [isShowingOriginal, setIsShowingOriginal] = useState(false);
  const hasOriginal = message.original !== message.text;

  return (
    <article className={isMine ? "bubble bubble--mine" : "bubble bubble--theirs"}>
      <p lang={isShowingOriginal ? message.original_lang : undefined}>
        {isShowingOriginal ? message.original : message.text}
      </p>
      {message.contacts_hidden && (
        <span className="bubble__hidden">
          <Icon name="lock" sizePx={14} />
          {t("chat.contactsHidden")}
        </span>
      )}
      {message.flagged && <Banner tone="info" title={message.flag_reason ?? t("translation.unsure")} />}
      {message.scam_warnings.map((warning) => (
        <Banner key={warning} tone="warning" title={warning} />
      ))}
      <footer className="bubble__meta">
        <time dateTime={message.sent_at}>{formatTime(message.sent_at, i18n.language)}</time>
        {hasOriginal && (
          <button type="button" className="text-toggle" onClick={() => setIsShowingOriginal(!isShowingOriginal)}>
            {isShowingOriginal ? t("translation.seeTranslation") : t("translation.seeOriginal")}
          </button>
        )}
      </footer>
    </article>
  );
}
