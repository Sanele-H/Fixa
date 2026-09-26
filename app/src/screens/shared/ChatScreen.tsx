// Chat between a job's customer and provider. The server translates every message, hides
// contact details until the job is confirmed, and refuses illegal requests.

import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { generatePath, useParams } from "react-router";
import { PATHS } from "../../app/paths";
import { MessageBubble } from "../../components/MessageBubble";
import { sampleJobPublic, sampleMe, sampleMessages, sampleProviderProfile } from "../../dev/samples";
import { Banner, IconButton, ScreenHeader, Slot } from "../../ui";

export default function ChatScreen() {
  const { t } = useTranslation();
  const { jobId = sampleJobPublic.id } = useParams();
  const me = sampleMe;

  /** Stops the page reloading. P1: send the message here. */
  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <main className="chat">
      <div className="screen">
        <ScreenHeader
          backTo={generatePath(PATHS.job, { jobId })}
          eyebrow={t("chat.eyebrow")}
          title={sampleProviderProfile.display_name}
        />
        <Banner tone="info" title={t("chat.privacyNote")} />
      </div>

      <section className="chat__messages" aria-live="polite" aria-label={t("chat.messages")}>
        {sampleMessages.map((message) => (
          <MessageBubble key={message.id} message={message} isMine={message.sender_id === me.id} />
        ))}
        <Slot
          label="poll every 3 s with ?after=, quote cards in the chat, refusal Banner when a message is blocked, drafts on poor signal"
          source="GET / POST /api/jobs/{job_id}/messages"
        />
      </section>

      <form className="composer" onSubmit={sendMessage}>
        <label className="visually-hidden" htmlFor="chat-composer">
          {t("chat.placeholder")}
        </label>
        <input id="chat-composer" className="composer__input" placeholder={t("chat.placeholder")} autoComplete="off" />
        <IconButton type="submit" icon="send" label={t("chat.send")} isInverse />
      </form>
    </main>
  );
}
