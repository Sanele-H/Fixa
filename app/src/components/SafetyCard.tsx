// Safety on the job's day, for the customer and the picked provider alike: the Emergency button,
// the safety timer, the trusted contact they text, and where each key moment happened.
// Only the person themselves sees their alerts and timers; the other person is never told.

import { useState, type FormEvent } from "react";
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
  type TrustedContact,
} from "../api/safety";
import type { JobState } from "../api/types";
import { formatDistanceKm, formatTime } from "../format";
import { Banner, Button, Card } from "../ui";
import { ErrorBanner } from "./ErrorBanner";

/** The job's day: from confirmed until it's finished. Safety tools show only then. */
const SAFETY_STATES: JobState[] = ["confirmed", "in_progress"];
/** Where it happened stays visible afterwards too, as a record. */
const MOMENT_STATES: JobState[] = ["confirmed", "in_progress", "done", "followed_up", "cancelled"];
/** A one-minute timer lets a demo show a missed timer; real use starts at half an hour. */
const TIMER_CHOICES = import.meta.env.DEV ? [1, 30, 60, 120] : [30, 60, 120];

/** Emergency numbers as text that can be read and dialled, with tel: links as a convenience. */
function EmergencyNumbers({ numbers }: { numbers: PanicResult["emergency_numbers"] }) {
  const { t } = useTranslation();
  return (
    <div className="stack">
      <p className="section-title">{t("safety.callNow")}</p>
      <div className="row">
        {numbers.map(({ label, number }) => (
          <a key={number} className="btn btn--secondary" href={`tel:${number}`}>
            {t(`safety.${label}`)}: {number}
          </a>
        ))}
      </div>
    </div>
  );
}

/** The red button, a confirm step (a panic press should never be an accident), and the result. */
function PanicButton({ jobId }: { jobId: string }) {
  const { t } = useTranslation();
  const panic = usePanic();
  const [isConfirming, setIsConfirming] = useState(false);

  if (panic.isSuccess) {
    const { contact, location_shared: locationShared, emergency_numbers: numbers } = panic.data;
    const sentText = contact
      ? t(locationShared ? "safety.panicSentTo" : "safety.panicSentNoLocation", { name: contact.name })
      : t("safety.panicNoContact");
    return (
      <Card tone="raised">
        <Banner tone={contact ? "info" : "warning"} title={sentText} />
        <EmergencyNumbers numbers={numbers} />
      </Card>
    );
  }
  if (isConfirming) {
    return (
      <Card tone="raised">
        <p className="section-title">{t("safety.panicConfirm")}</p>
        <p className="small">{t("safety.panicConfirmBody")}</p>
        {panic.isError && <ErrorBanner error={panic.error} />}
        <div className="row">
          <Button variant="danger" onClick={() => panic.mutate(jobId)} disabled={panic.isPending}>
            {t("safety.panicYes")}
          </Button>
          <Button variant="secondary" onClick={() => setIsConfirming(false)}>
            {t("safety.panicNo")}
          </Button>
        </div>
      </Card>
    );
  }
  return (
    <Button variant="danger" isBlock icon="alert" onClick={() => setIsConfirming(true)}>
      {t("safety.panic")}
    </Button>
  );
}

/** "Check on me in an hour", then "I'm safe"; says so if it ran out. */
function SafetyTimerControls({ jobId, hasContact }: { jobId: string; hasContact: boolean }) {
  const { t, i18n } = useTranslation();
  const timer = useSafetyTimer(jobId);
  const startTimer = useStartSafetyTimer(jobId);
  const saySafe = useSaySafe(jobId);
  const current = timer.data;
  const actionError = startTimer.error ?? saySafe.error;

  return (
    <div className="stack">
      <p className="section-title">{t("safety.timerTitle")}</p>
      {current?.state === "running" ? (
        <>
          <p className="small">
            {t("safety.timerRunning", { time: formatTime(current.due_at, i18n.language) })}
          </p>
          <Button variant="lime" isBlock icon="check" onClick={() => saySafe.mutate()} disabled={saySafe.isPending}>
            {t("safety.imSafe")}
          </Button>
        </>
      ) : (
        <>
          {current?.state === "missed" && (
            <Banner
              tone="warning"
              title={t(hasContact ? "safety.timerMissed" : "safety.timerMissedNoContact")}
            />
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
