// Values the frontend shares with the backend. Keep in sync with backend/fixa/domain/.

/** Replaces a hidden phone number/email/address in chat (backend/fixa/domain/tokens.py). */
export const MASKED_CONTACT_TOKEN = "[***]";

/** How often chat and job lists refresh. Polling is simpler and sturdier than websockets on venue Wi-Fi. */
export const POLLING_INTERVAL_IN_MILLISECONDS = 2000;

/** Job states, in order (backend/fixa/domain/job_states.py). */
export const JOB_STATES = ["posted", "quoted", "accepted", "confirmed", "unlocked"];
