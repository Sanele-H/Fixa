// One job: quotes, the approval steps, chat, and the unlocked contact details.
// Demo steps 2-4 all happen here, on both phones.
//
// TODO (Role 2, Day 2-4), probably as separate components:
// - QuotePanel: provider sends price (R) + day/time; customer sees quotes and taps Accept.
//   Format times with Intl.DateTimeFormat(languageCode, ...) so "Tuesday" shows as
//   "Dinsdag" / "ULwesibili" without any translation.
// - Approval steps: customer Accept -> provider Confirm -> Unlock. Show where the job is.
// - ChatPanel: api.listMessages polled with usePolling, MessageBubble per message, send box.
// - ContactDetailsPanel: "hidden until you both approve", then phone (and address for the
//   provider) from api.getContactDetails once the job is unlocked.

import { useState } from "react";

import { api } from "../api/client.js";
import MessageBubble from "../components/MessageBubble.jsx";
import usePolling from "../hooks/usePolling.js";
import { getUiString } from "../i18n/strings.js";

export default function JobDetailScreen({ currentUser, job, languageCode, onBack }) {
  const [messages, setMessages] = useState([]);
  const otherUserId = currentUser.role === "customer" ? job.offeredProviderIds[0] : job.customerId;

  usePolling(() => api.listMessages(job.id, otherUserId).then(setMessages));

  return (
    <section>
      <button type="button" onClick={onBack}>
        {getUiString(languageCode, "back")}
      </button>
      <h1>{job.description}</h1>
      <p className="placeholder">TODO Role 2: quotes, accept / confirm / unlock, contact details.</p>
      <div className="chat">
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isMine={message.senderId === currentUser.id}
            languageCode={languageCode}
          />
        ))}
      </div>
    </section>
  );
}
