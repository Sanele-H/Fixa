import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { Language, Message } from "../api/types";
import { formatTime } from "../format";
import { LANGUAGE_NAMES } from "../i18n";
import { Banner, Button, Icon } from "../ui";
import { ReportButton } from "./ReportButton";

type MessageBubbleProps = {
  message: Message;
  isMine: boolean;
  /** The app's language. A message written in another one can be translated into it. */
  appLanguage: Language;
  /** True once the reader chose to translate this chat. */
  isTranslating: boolean;
  /**
   * Given on the newest message in another language while the chat isn't translated yet:
   * it shows "This message is in isiZulu" with a "Translate to English" button.
   */
  onTranslate?: () => void;
};

/**
 * One chat message, shown as it was written. When it's in another language the reader can
 * translate it (the server sends the translation in `text`), and then flip back to the
 * original. Your own messages always show as you wrote them. Hidden contact details and
 * scam warnings always show, translated or not.
 */
export function MessageBubble({ message, isMine, appLanguage, isTranslating, onTranslate }: MessageBubbleProps) {
  const { t, i18n } = useTranslation();
  const [isShowingOriginal, setIsShowingOriginal] = useState(false);
  const isOtherLanguage = !isMine && message.original_lang !== appLanguage;
  const isShowingTranslation = isOtherLanguage && isTranslating && !isShowingOriginal;

  return (
    <article className={isMine ? "bubble bubble--mine" : "bubble bubble--theirs"}>
      <p lang={isShowingTranslation ? appLanguage : message.original_lang}>
        {isShowingTranslation ? message.text : message.original}
      </p>
      {isOtherLanguage && !isTranslating && onTranslate && (
        <div className="bubble__translate">
          <p className="small">{t("translation.messageIn", { language: LANGUAGE_NAMES[message.original_lang] })}</p>
          <Button variant="lime" isSmall icon="globe" onClick={onTranslate}>
            {t("translation.translateTo", { language: LANGUAGE_NAMES[appLanguage] })}
          </Button>
        </div>
      )}
      {message.contacts_hidden && (
        <span className="bubble__hidden">
          <Icon name="lock" sizePx={14} />
          {t("chat.contactsHidden")}
        </span>
      )}
      {isShowingTranslation && message.flagged && (
        <Banner tone="info" title={message.flag_reason ?? t("translation.unsure")} />
      )}
      {message.scam_warnings.map((warning) => (
        <Banner key={warning} tone="warning" title={warning} />
      ))}
      {!isMine && <ReportButton targetType="message" targetId={message.id} />}
      <footer className="bubble__meta">
        <time dateTime={message.sent_at}>{formatTime(message.sent_at, i18n.language)}</time>
        {isOtherLanguage && isTranslating && (
          <button type="button" className="text-toggle" onClick={() => setIsShowingOriginal(!isShowingOriginal)}>
            {isShowingOriginal ? t("translation.seeTranslation") : t("translation.seeOriginal")}
          </button>
        )}
      </footer>
    </article>
  );
}
