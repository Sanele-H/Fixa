"""The inbox behind the bell, and the push notification that goes with each item.

notify() is called right after something happens (a quote, a confirmed job, a message, a check-in,
a safety alert). It stores the item and sends a push to the person's phones. Texts come back in
the reader's language, like everything else a person reads. isiZulu by P3 (first-language
speaker); isiXhosa falls back to English until an isiXhosa speaker writes it.
"""

import datetime as dt
import uuid
from typing import Any

from sqlmodel import Session, select

from fixa_api import push
from fixa_api.models import Customer, Notification, Provider

FALLBACK_LANG = "en"
INBOX_LIMIT = 50

# kind -> language -> (title, body). Fill-ins: {name}, {amount}, {contact}.
TEXTS: dict[str, dict[str, tuple[str, str]]] = {
    "quote_received": {
        "en": ("New quote", "{name} quoted R{amount} for your job."),
        "zu": ("Intengo entsha", "U-{name} uthumele intengo ka-R{amount} yomsebenzi wakho."),
    },
    "quote_accepted": {
        "en": (
            "Your quote was accepted",
            "{name} accepted your R{amount} quote. Confirm the job to see their details.",
        ),
        "zu": (
            "Intengo yakho yamukelwe",
            "U-{name} wamukele intengo yakho ka-R{amount}. Qinisekisa umsebenzi ukuze ubone "
            "imininingwane yakhe.",
        ),
    },
    "job_confirmed": {
        "en": ("Job confirmed", "{name} confirmed your job. You can now see each other's number."),
        "zu": (
            "Umsebenzi uqinisekisiwe",
            "U-{name} uqinisekise umsebenzi wakho. Manje senibona izinombolo zomunye nomunye.",
        ),
    },
    "job_declined": {
        "en": ("Quote withdrawn", "{name} can't take the job. Pick another quote."),
        "zu": (
            "Akakwazi ukuwuthatha",
            "U-{name} akakwazi ukuthatha umsebenzi. Khetha enye intengo.",
        ),
    },
    "message": {
        "en": ("New message", "{name} sent you a message."),
        "zu": ("Umlayezo omusha", "U-{name} ukuthumelele umlayezo."),
    },
    "on_my_way": {
        "en": ("{name} is on the way", "{name} is on the way to your job."),
        "zu": ("U-{name} usendleleni", "U-{name} usendleleni eza emsebenzini wakho."),
    },
    "timer_check": {
        "en": (
            "Are you OK?",
            "Your safety timer is up. Open Fixa and tap \u201cI'm safe\u201d, "
            "or we'll alert your trusted contact.",
        ),
        "zu": (
            "Uphephile?",
            "Isikhathi sakho sokuphepha siphelile. Vula i-Fixa ucindezele ethi "
            "\u201cNgiphephile\u201d, noma sizokwazisa umuntu omethembayo.",
        ),
    },
    "checked_in": {
        "en": ("{name} has arrived", "{name} checked in for your job."),
        "zu": ("U-{name} ufikile", "U-{name} usho ukuthi ufikile emsebenzini wakho."),
    },
    "checked_out": {
        "en": ("Work finished", "{name} says the work is finished. Is it done?"),
        "zu": ("Umsebenzi uphelile", "U-{name} uthi umsebenzi uphelile. Ingabe wenziwe?"),
    },
    "job_done": {
        "en": ("Job done", "{name} marked the job as done. It now counts on your record."),
        "zu": (
            "Umsebenzi wenziwe",
            "U-{name} uthe umsebenzi wenziwe. Manje ubalwa kurekhodi lakho.",
        ),
    },
    "panic_sent": {
        "en": (
            "Alert sent",
            "We sent your location to {contact}. If you're in danger, call 10111 or 112.",
        ),
        "zu": (
            "Isexwayiso sithunyelwe",
            "Sithumele indawo okuyo ku-{contact}. Uma usengozini, shayela u-10111 noma u-112.",
        ),
    },
    "panic_not_sent": {
        "en": (
            "Alert not sent",
            "We couldn't text {contact}. Send it on WhatsApp from the job, "
            "or call 10111 or 112 if you're in danger.",
        ),
        "zu": (
            "Isexwayiso asithunyelwanga",
            "Asikwazanga ukuthumela umlayezo ku-{contact}. Sithumele nge-WhatsApp emsebenzini, "
            "noma ushayele u-10111 noma u-112 uma usengozini.",
        ),
    },
    "panic_no_contact": {
        "en": (
            "Alert recorded",
            "Add a trusted contact so someone is told next time. "
            "If you're in danger, call 10111 or 112.",
        ),
        "zu": (
            "Isexwayiso silotshiwe",
            "Engeza umuntu omethembayo ukuze atshelwe ngokuzayo. "
            "Uma usengozini, shayela u-10111 noma u-112.",
        ),
    },
    "timer_missed": {
        "en": ("Safety timer ran out", "You didn't say you were safe, so we let {contact} know."),
        "zu": (
            "Isikhathi sokuphepha siphelile",
            "Awuzange usho ukuthi uphephile, ngakho sazise u-{contact}.",
        ),
    },
    "timer_missed_not_sent": {
        "en": (
            "Safety timer ran out",
            "You didn't say you were safe, and we couldn't text {contact}. "
            "Open the job to send it on WhatsApp.",
        ),
        "zu": (
            "Isikhathi sokuphepha siphelile",
            "Awuzange usho ukuthi uphephile, futhi asikwazanga ukuthumela umlayezo ku-{contact}. "
            "Vula umsebenzi ukuze uwuthumele nge-WhatsApp.",
        ),
    },
    "payment_change_asked": {
        "en": (
            "Change how you pay?",
            "{name} asked to change how this job is paid. Open it to answer.",
        ),
        "zu": (
            "Shintsha indlela yokukhokha?",
            "U-{name} ucele ukushintsha indlela yokukhokhela lo msebenzi. Wuvule ukuze uphendule.",
        ),
    },
    "payment_change_agreed": {
        "en": ("Payment plan changed", "{name} agreed. The job is now paid the new way."),
        "zu": (
            "Indlela yokukhokha ishintshile",
            "U-{name} uvumile. Manje umsebenzi ukhokhelwa ngendlela entsha.",
        ),
    },
    "payment_change_declined": {
        "en": ("Payment plan kept", "{name} would rather keep the payment plan as it is."),
        "zu": (
            "Indlela yokukhokha ayishintshile",
            "U-{name} ukhetha ukugcina indlela yokukhokha injalo.",
        ),
    },
    "payment_received": {
        "en": ("Payment received", "{name} paid R{amount} in the app."),
        "zu": ("Inkokhelo itholakele", "U-{name} ukhokhe u-R{amount} ku-app."),
    },
    "payment_receipt": {
        "en": ("Payment done", "You paid R{amount}. Your receipt is on the job."),
        "zu": ("Ukukhokha kuphelile", "Ukhokhe u-R{amount}. Irisidi yakho isemsebenzini."),
    },
    "timer_missed_no_contact": {
        "en": (
            "Safety timer ran out",
            "You didn't say you were safe. Add a trusted contact so someone is told next time.",
        ),
        "zu": (
            "Isikhathi sokuphepha siphelile",
            "Awuzange usho ukuthi uphephile. Engeza umuntu omethembayo ukuze atshelwe ngokuzayo.",
        ),
    },
}


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def render(kind: str, params: dict[str, Any], lang: str) -> tuple[str, str]:
    """The (title, body) for one item in the reader's language, English if there's no text yet."""
    texts = TEXTS.get(kind)
    if texts is None:
        return kind, ""
    title, body = texts.get(lang) or texts[FALLBACK_LANG]
    return title.format(**params), body.format(**params)


def job_url(job_id: str | None) -> str:
    return f"/jobs/{job_id}" if job_id else "/inbox"


def notify(
    session: Session,
    user: Customer | Provider | None,
    kind: str,
    job_id: str | None = None,
    **params: Any,
) -> None:
    """Add an item to the person's inbox and push it to their phones. Commits on its own, so call
    it after the change it's about has been saved."""
    if user is None:
        return
    session.add(
        Notification(
            id=f"note_{uuid.uuid4().hex[:10]}",
            user_id=user.id,
            job_id=job_id,
            kind=kind,
            params=params,
            created_at=now(),
        )
    )
    session.commit()
    title, body = render(kind, params, user.lang)
    push.send_to_user(user.id, title, body, job_url(job_id))


def notification_view(notification: Notification, lang: str) -> dict[str, Any]:
    title, body = render(notification.kind, notification.params, lang)
    return {
        "id": notification.id,
        "kind": notification.kind,
        "title": title,
        "body": body,
        "job_id": notification.job_id,
        "created_at": notification.created_at.isoformat(),
        "read": notification.read_at is not None,
    }


def read_inbox(session: Session, user: Customer | Provider) -> dict[str, Any]:
    """The newest items first, and how many are unread."""
    query = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(INBOX_LIMIT)
    )
    items = session.exec(query).all()
    return {
        "unread": sum(item.read_at is None for item in items),
        "items": [notification_view(item, user.lang) for item in items],
    }


def mark_read(session: Session, user: Customer | Provider, notification_id: str | None) -> None:
    """Mark one item read, or all of them when notification_id is None."""
    query = select(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    )
    if notification_id is not None:
        query = query.where(Notification.id == notification_id)
    for item in session.exec(query):
        item.read_at = now()
        session.add(item)
    session.commit()
