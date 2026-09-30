// Safety on the job's day, for the customer and the picked provider alike: the Emergency button,
// the safety timer, the trusted contact they text (with WhatsApp as a second way to tell them),
// and where each key moment happened.
// Only the person themselves sees their alerts and timers; the other person is never told.

import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import {
  usePanic,
  useSafetyTimer,
  useSaySafe,
  useSaveTrustedContact,
  useStartSafetyTimer,
  useTrustedContact,
  useJobLocations,
  type PanicResult,
  type SafetyTimer,
  type TrustedContact,
} from "../api/safety";
import type { JobState } from "../api/types";
import { formatDistanceKm, formatTime } from "../format";
import { Banner, Button, Card, Icon } from "../ui";
import { ErrorBanner } from "./ErrorBanner";

/** The job's day: from confirmed until it's finished. Safety tools show only then. */
const SAFETY_STATES: JobState[] = ["confirmed", "in_progress"];
/** Where it happened stays visible afterwards too, as a record. */
const MOMENT_STATES: JobState[] = ["confirmed", "in_progress", "done", "followed_up", "cancelled"];
/** A one-minute timer lets a demo show a missed timer; real use starts at half an hour. */
const TIMER_CHOICES = import.meta.env.DEV ? [1, 30, 60, 120] : [30, 60, 120];

/** How long Emergency must be held, so a pocket or a stray tap never sends an alert. */
const HOLD_TO_PANIC_MS = 3_000;

/**
 * Opens WhatsApp with the alert already written, addressed to the trusted contact. The SMS can
 * fail (or, on the sandbox, never reach a real phone), so this is always offered as well.
 */
function WhatsAppAlertLink({ url }: { url: string }) {
  const { t } = useTranslation();
  return (
    <a className="btn btn--secondary btn--block" href={url} target="_blank" rel="noopener noreferrer">
      {t("safety.sendOnWhatsApp")}
    </a>
  );
}

/** What to tell the person after a panic: only say it was sent when the SMS really went. */
function getPanicResultKey(result: PanicResult) {
  if (!result.contact) {
    return "safety.panicNoContact";
  }
  if (!result.sms_sent) {
    return "safety.panicNotSent";
  }
  return result.location_shared ? "safety.panicSentTo" : "safety.panicSentNoLocation";
}

type PanicResultCardProps = { result: PanicResult };

/**
 * What happens after Emergency: who was told (only "sent" when the SMS really went), then the
 * two things to do next, big and first: call the police, and send the same alert on WhatsApp to
 * the trusted contact. They're buttons rather than opening by themselves: a phone can only open one app at a
 * time, and a call should never start without a tap.
 */
function PanicResultCard({ result }: PanicResultCardProps) {
  const { t } = useTranslation();
  const { contact, emergency_numbers: numbers, whatsapp_url: whatsappUrl } = result;
  const isSent = Boolean(contact) && result.sms_sent;
  const [police, ...others] = numbers;

  return (
    <Card tone="raised">
      <Banner tone={isSent ? "info" : "warning"} title={t(getPanicResultKey(result), { name: contact?.name })} />
      <p className="section-title">{t("safety.callNow")}</p>
      {police && (
        <a className="btn btn--danger btn--block" href={`tel:${police.number}`}>
          <Icon name="phone" />
          {t(`safety.${police.label}`)}: {police.number}
        </a>
      )}
      {whatsappUrl && contact && (
        <a className="btn btn--lime btn--block" href={whatsappUrl} target="_blank" rel="noopener noreferrer">
          <Icon name="send" />
          {t("safety.sendWhatsApp", { name: contact.name })}
        </a>
      )}
      <div className="row">
        {others.map(({ label, number }) => (
          <a key={number} className="btn btn--secondary btn--small" href={`tel:${number}`}>
            {t(`safety.${label}`)}: {number}
          </a>
        ))}
      </div>
    </Card>
  );
}

/** Hold for 3 seconds to send an alert; letting go early cancels it. Works with touch, mouse and keys. */
function PanicButton({ jobId }: { jobId: string }) {
  const { t } = useTranslation();
  const panic = usePanic();
  const [isHolding, setIsHolding] = useState(false);
  const holdTimeout = useRef<number | null>(null);

  useEffect(() => () => {
    if (holdTimeout.current !== null) {
      window.clearTimeout(holdTimeout.current);
    }
  }, []);

  function startHold() {
    if (panic.isPending || holdTimeout.current !== null) {
      return;
    }
    setIsHolding(true);
    holdTimeout.current = window.setTimeout(() => {
      holdTimeout.current = null;
      setIsHolding(false);
      panic.mutate(jobId);
    }, HOLD_TO_PANIC_MS);
  }

  function cancelHold() {
    if (holdTimeout.current !== null) {
      window.clearTimeout(holdTimeout.current);
      holdTimeout.current = null;
    }
    setIsHolding(false);
  }

  if (panic.isSuccess) {
    return <PanicResultCard result={panic.data} />;
  }
  return (
    <div className="stack">
      <button
        type="button"
        className={isHolding ? "btn btn--danger btn--block hold-button is-holding" : "btn btn--danger btn--block hold-button"}
        style={{ "--hold-ms": `${HOLD_TO_PANIC_MS}ms` } as CSSProperties}
        onPointerDown={startHold}
        onPointerUp={cancelHold}
        onPointerLeave={cancelHold}
        onPointerCancel={cancelHold}
        onKeyDown={(event) => {
          if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
            event.preventDefault();
            startHold();
          }
        }}
        onKeyUp={cancelHold}
        onContextMenu={(event) => event.preventDefault()}
        disabled={panic.isPending}
        aria-describedby="panic-hold-hint"
      >
        <Icon name="alert" />
        <span>{isHolding ? t("safety.panicHolding") : t("safety.panic")}</span>
      </button>
      <p id="panic-hold-hint" className="small muted">
        {t("safety.holdToPanic")}
      </p>
      {panic.isError && <ErrorBanner error={panic.error} />}
    </div>
  );
}

/** What to say when a timer ran out: texted the contact, couldn't, or there's nobody to tell. */
function getMissedTimerKey(timer: SafetyTimer, hasContact: boolean) {
  if (!hasContact) {
    return "safety.timerMissedNoContact";
  }
  return timer.contact_notified ? "safety.timerMissed" : "safety.timerMissedNotSent";
}

/** "Check on me in an hour", "Are you OK?" when it's up, then "I'm safe"; says so if it ran out. */
function SafetyTimerControls({ jobId, hasContact }: { jobId: string; hasContact: boolean }) {
  const { t, i18n } = useTranslation();
  const timer = useSafetyTimer(jobId);
  const startTimer = useStartSafetyTimer(jobId);
  const saySafe = useSaySafe(jobId);
  const current = timer.data;
  const actionError = startTimer.error ?? saySafe.error;
  const imSafeButton = (
    <Button variant="lime" isBlock icon="check" onClick={() => saySafe.mutate()} disabled={saySafe.isPending}>
      {t("safety.imSafe")}
    </Button>
  );

  if (current?.state === "asking") {
    return (
      <div className="stack" role="alert">
        <p className="section-title">{t("safety.areYouOk")}</p>
        <p className="small">{t("safety.areYouOkBody", { time: formatTime(current.alert_at, i18n.language) })}</p>
        {imSafeButton}
        {actionError && <ErrorBanner error={actionError} />}
      </div>
    );
  }
  return (
    <div className="stack">
      <p className="section-title">{t("safety.timerTitle")}</p>
      {current?.state === "running" ? (
        <>
          <p className="small">
            {t("safety.timerRunning", { time: formatTime(current.due_at, i18n.language) })}
          </p>
          {current.reason === "check_in" && <p className="small muted">{t("safety.timerFromCheckIn")}</p>}
          {imSafeButton}
        </>
      ) : (
        <>
          {current?.state === "missed" && (
            <>
              <Banner tone="warning" title={t(getMissedTimerKey(current, hasContact))} />
              {current.whatsapp_url && <WhatsAppAlertLink url={current.whatsapp_url} />}
            </>
          )}
          {current?.state === "safe" && <Banner tone="info" title={t("safety.timerSafe")} />}
          <p className="small">{t("safety.timerBody")}</p>
          <div className="row">
            {TIMER_CHOICES.map((minutes) => (
              <Button
                key={minutes}
                variant="secondary"
                isSmall
                icon="clock"
                onClick={() => startTimer.mutate(minutes)}
                disabled={startTimer.isPending}
              >
                {t(`safety.timer${minutes}`)}
              </Button>
            ))}
          </div>
        </>
      )}
      {actionError && <ErrorBanner error={actionError} />}
    </div>
  );
}

/** Shows the trusted contact, or a small form to add or change one. */
function TrustedContactEditor({ contact }: { contact: TrustedContact | null }) {
  const { t } = useTranslation();
  const saveContact = useSaveTrustedContact();
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(contact?.name ?? "");
  const [phone, setPhone] = useState(contact?.phone ?? "");

  function save(event: FormEvent) {
    event.preventDefault();
    saveContact.mutate({ name, phone }, { onSuccess: () => setIsEditing(false) });
  }

  if (contact && !isEditing) {
    return (
      <div className="row row--between">
        <div>
          <p className="section-title">{t("safety.contactTitle")}</p>
          <p className="small">{t("safety.contactIs", contact)}</p>
        </div>
        <Button variant="secondary" isSmall onClick={() => setIsEditing(true)}>
          {t("safety.contactChange")}
        </Button>
      </div>
    );
  }
  return (
    <form className="stack" onSubmit={save}>
      <p className="section-title">{t("safety.contactTitle")}</p>
      {!contact && <p className="small">{t("safety.contactNone")}</p>}
      <div className="field">
        <label className="field__label" htmlFor="trusted-contact-name">
          {t("safety.contactName")}
        </label>
        <input
          id="trusted-contact-name"
          className="field__input"
          value={name}
          onChange={(event) => setName(event.target.value)}
          autoComplete="off"
          required
          maxLength={60}
        />
      </div>
      <div className="field">
        <label className="field__label" htmlFor="trusted-contact-phone">
          {t("safety.contactPhone")}
        </label>
        <input
          id="trusted-contact-phone"
          className="field__input"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          inputMode="tel"
          autoComplete="off"
          placeholder="082 555 0101"
          required
          minLength={9}
          maxLength={20}
        />
      </div>
      {saveContact.isError && <ErrorBanner error={saveContact.error} />}
      <Button type="submit" variant="secondary" isBlock disabled={saveContact.isPending}>
        {t("safety.contactSave")}
      </Button>
    </form>
  );
}

/** Each key moment and how far from the job address it happened. Never a map or coordinates. */
function KeyMoments({ jobId }: { jobId: string }) {
  const { t, i18n } = useTranslation();
  const locations = useJobLocations(jobId);

  if (!locations.data?.length) {
    return null;
  }
  return (
    <Card>
      <p className="section-title">{t("safety.momentsTitle")}</p>
      <ul className="stack moment-list">
        {locations.data.map((entry) => (
          <li key={`${entry.moment}-${entry.at}`}>
            <p>{t(`safety.moment.${entry.moment}`, { name: entry.name })}</p>
            <p className="small muted">
              {formatTime(entry.at, i18n.language)} ·{" "}
              {t("safety.distanceFromJob", { distance: formatDistanceKm(entry.distance_km) })}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/** Everything safety-related for one job, for whoever is looking at it. */
export function SafetyCard({ jobId, state }: { jobId: string; state: JobState }) {
  const { t } = useTranslation();
  const contact = useTrustedContact();
  const showsTools = SAFETY_STATES.includes(state);

  return (
    <>
      {showsTools && (
        <Card tone="raised">
          <div className="row row--between">
            <h2 className="section-title">{t("safety.title")}</h2>
          </div>
          <p className="small muted">{t("safety.intro")}</p>
          <PanicButton jobId={jobId} />
          <SafetyTimerControls jobId={jobId} hasContact={Boolean(contact.data)} />
          {contact.isSuccess && <TrustedContactEditor key={contact.data?.phone ?? "none"} contact={contact.data} />}
        </Card>
      )}
      {MOMENT_STATES.includes(state) && <KeyMoments jobId={jobId} />}
    </>
  );
}
