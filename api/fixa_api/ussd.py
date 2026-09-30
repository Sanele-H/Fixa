"""The USSD menu for confirming an off-app job, for customers on feature phones with no data.

Africa's Talking calls the API with the dialled number and everything typed so far in `text`
(choices joined by "*", empty on the first screen). The answer starts with CON (keep the session
going) or END (finish). The phone number comes from the phone network, so no code is needed, but
the callback address carries the same secret as the SMS webhook.

Screens: which job (only if several are waiting) -> "is that right?" -> "may we list you as a
reference?" -> done. A confirmation by USSD follows exactly the same rules as one by SMS.
"""

from sqlmodel import Session

from fixa_api.models import OffAppConfirmation, OffAppJob, Provider
from fixa_api.off_app import apply_answer, pending_for_phone
from fixa_api.ussd_texts import (
    ANSWER_NO,
    ANSWER_YES,
    MAX_JOBS_LISTED,
    MENU_TASK_LIMIT,
    text_for,
)

CONTINUE = "CON "
END = "END "


def _end(lang: str, key: str, **values: str) -> str:
    return END + text_for(lang, key, **values)


def _details(session: Session, job: OffAppJob, confirmation: OffAppConfirmation) -> dict[str, str]:
    provider = session.get(Provider, job.provider_id)
    return {
        "provider": provider.display_name,
        "task": job.trade_task,
        "suburb": job.suburb,
        "date": job.date.isoformat(),
    }


def ussd_reply(session: Session, phone: str, text: str) -> str:
    """The next USSD screen for this number, given what they have typed so far."""
    pending = pending_for_phone(session, phone)[:MAX_JOBS_LISTED]
    if not pending:
        return _end("en", "nothing_waiting")
    choices = text.split("*") if text else []
    lang = pending[0][1].lang

    if len(pending) > 1:  # several jobs are waiting: pick one first
        if not choices:
            lines = [
                f"{number}. {_details(session, job, conf)['provider']}: "
                f"{job.trade_task[:MENU_TASK_LIMIT]}"
                for number, (job, conf) in enumerate(pending, start=1)
            ]
            return CONTINUE + text_for(lang, "which_job") + "\n" + "\n".join(lines)
        if not choices[0].isdigit() or not 1 <= int(choices[0]) <= len(pending):
            return _end(lang, "invalid")
        pending, choices = [pending[int(choices[0]) - 1]], choices[1:]

    job, confirmation = pending[0]
    lang = confirmation.lang
    details = _details(session, job, confirmation)
    if not choices:
        return CONTINUE + text_for(lang, "ask", **details)
    if choices[0] not in (ANSWER_YES, ANSWER_NO):
        return _end(lang, "invalid")
    if choices[0] == ANSWER_NO:
        apply_answer(session, job, "ussd", said_yes=False, agrees_to_be_reference=False)
        return _end(lang, "declined")
    if len(choices) == 1:
        return CONTINUE + text_for(lang, "ask_reference", provider=details["provider"])
    if choices[1] not in (ANSWER_YES, ANSWER_NO):
        return _end(lang, "invalid")
    apply_answer(
        session, job, "ussd", said_yes=True, agrees_to_be_reference=choices[1] == ANSWER_YES
    )
    return _end(lang, "confirmed")
