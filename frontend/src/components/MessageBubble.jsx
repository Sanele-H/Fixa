// One chat message. The sender sees what they typed; the reader sees the translation.
//
// TODO (Role 2, Day 3):
// - "See original" toggle on received messages (shows originalText + its language).
// - Render MASKED_CONTACT_TOKEN as a localised "number hidden" chip, not the raw "[***]".
// - Small "unsure" marker when translationFlags is not empty.
// - Scam warnings (message.scamWarnings codes) as a clear banner, from i18n strings.
// - Highlight prices and times so it's obvious they came through unchanged.

export default function MessageBubble({ message, isMine }) {
  const textForViewer = isMine ? message.originalText : message.translatedText;

  return (
    <div className={isMine ? "bubble bubble-mine" : "bubble bubble-theirs"}>
      {textForViewer}
    </div>
  );
}
