"""Agreeing how a job is paid: the plan, changing it, and what the customer owes when.

Three ways to pay (models.PAYMENT_METHODS):

- in_app_after: the full amount in the app once the customer says "It's done".
- in_app_split: a deposit once the provider confirms, the balance at "It's done". The deposit
  is at most half the quote, so a provider can't take most of the money before any work.
- cash: paid off the app. Fixa shows the amount and never touches the money.

The quote says which ways the provider accepts; the customer picks one when accepting. After
that the plan changes only when both agree, and only before the work starts and before any
money has moved.
"""

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, select

from fixa_api import job_states as states
from fixa_api.models import (
    PAYMENT_METHODS,
    Customer,
    Job,
    Payment,
    PaymentPlan,
    PaymentPlanChange,
    Provider,
    Quote,
)

IN_APP_AFTER, IN_APP_SPLIT, CASH = PAYMENT_METHODS
MAX_DEPOSIT_SHARE = 0.5  # a deposit is at most half the quote

# The plan can change only before the work starts.
CHANGEABLE_STATES = {states.QUOTE_ACCEPTED, states.CONFIRMED}
# A deposit is asked for once the provider has confirmed, until the work is done.
DEPOSIT_STATES = {states.CONFIRMED, states.IN_PROGRESS}
# The rest is asked for once the customer says the job is done.
BALANCE_STATES = {states.DONE, states.FOLLOWED_UP}

PENDING, PAID, FAILED, CANCELLED = "pending", "paid", "failed", "cancelled"
AGREED, DECLINED, WITHDRAWN = "agreed", "declined", "withdrawn"


@dataclass(frozen=True)
class AmountDue:
    """What the customer can pay in the app right now. kind: deposit, balance (the rest after a
    deposit) or full (everything, when nothing has been paid yet)."""

    kind: str
    amount_rands: int


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def refuse(status_code: int, code: str, message: str) -> HTTPException:
    """The error the app reads: {"error": code, "message": message}."""
    return HTTPException(status_code=status_code, detail={"error": code, "message": message})


def find_largest_deposit(total_rands: int) -> int:
    """The biggest deposit allowed on a quote: half, rounded down to whole rands."""
    return int(total_rands * MAX_DEPOSIT_SHARE)


def check_deposit(method: str, deposit_rands: int | None, total_rands: int) -> int:
    """The deposit to store for this method: 0 unless it's in_app_split, which needs one from
    R1 up to half the total. Raises 422 deposit_required or deposit_too_high."""
    if method != IN_APP_SPLIT:
        return 0
    if not deposit_rands or deposit_rands < 1:
        raise refuse(422, "deposit_required", "A split payment needs a deposit")
    if deposit_rands > find_largest_deposit(total_rands):
        raise refuse(422, "deposit_too_high", "A deposit can be at most half the price")
    return deposit_rands


def read_plan(session: Session, job_id: str) -> PaymentPlan | None:
    return session.get(PaymentPlan, job_id)


def create_plan(session: Session, job: Job, quote: Quote, method: str | None) -> PaymentPlan:
    """The plan for the quote the customer just accepted. With no method given, the quote's
    first one (older apps don't send one). Raises 422 payment_method_not_offered for a way to
    pay the provider didn't offer. Added to the session; the caller commits."""
    chosen_method = method or quote.payment_methods[0]
    if chosen_method not in quote.payment_methods:
        raise refuse(422, "payment_method_not_offered", "This provider doesn't take that payment")
    plan = PaymentPlan(
        job_id=job.id,
        quote_id=quote.id,
        method=chosen_method,
        total_rands=quote.amount_rands,
        deposit_rands=check_deposit(chosen_method, quote.deposit_rands, quote.amount_rands),
        agreed_at=now(),
    )
    session.add(plan)
    return plan


def list_payments(session: Session, job_id: str) -> list[Payment]:
    query = select(Payment).where(Payment.job_id == job_id).order_by(Payment.created_at)
    return list(session.exec(query))


def sum_paid_rands(payments: list[Payment]) -> int:
    return sum(payment.amount_rands for payment in payments if payment.state == PAID)


def cancel_pending_payments(session: Session, job_id: str) -> None:
    """Stops checkouts that haven't finished, when the amount or plan they were for changed. A
    confirmation that still arrives for one is refused (see confirm_payment)."""
    for payment in list_payments(session, job_id):
        if payment.state == PENDING:
            payment.state = CANCELLED
            session.add(payment)


def read_pending_change(session: Session, job_id: str) -> PaymentPlanChange | None:
    query = select(PaymentPlanChange).where(
        PaymentPlanChange.job_id == job_id, PaymentPlanChange.state == PENDING
    )
    return session.exec(query).first()


def delete_plan(session: Session, job_id: str) -> None:
    """Drops the plan when the provider turns the job down: the next accepted quote brings its
    own. Nothing can have been paid yet, since payments start at confirmed. The caller commits."""
    plan = read_plan(session, job_id)
    if plan is None:
        return
    change = read_pending_change(session, job_id)
    if change is not None:
        change.state, change.decided_at = WITHDRAWN, now()
        session.add(change)
    cancel_pending_payments(session, job_id)
    session.delete(plan)


def find_amount_due(job: Job, plan: PaymentPlan | None, paid_rands: int) -> AmountDue | None:
    """What the customer can pay in the app now, or None: a cash plan, everything paid, or not
    the moment yet. The deposit is due from confirmed; the rest from "It's done"."""
    if plan is None or plan.method == CASH:
        return None
    remaining_rands = plan.total_rands - paid_rands
    if remaining_rands <= 0:
        return None
    if job.state in BALANCE_STATES:
        return AmountDue("balance" if paid_rands else "full", remaining_rands)
    if job.state in DEPOSIT_STATES and plan.method == IN_APP_SPLIT and paid_rands == 0:
        return AmountDue("deposit", plan.deposit_rands)
    return None


def can_change_plan(job: Job, plan: PaymentPlan | None, paid_rands: int) -> bool:
    """True before the work starts and before any money has moved."""
    return plan is not None and job.state in CHANGEABLE_STATES and paid_rands == 0


def receipt_view(payment: Payment) -> dict[str, Any]:
    return {
        "id": payment.id,
        "kind": payment.kind,
        "amount_rands": payment.amount_rands,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "gateway": payment.gateway,
        "reference": payment.gateway_reference,
    }


def change_view(change: PaymentPlanChange, viewer: Customer | Provider) -> dict[str, Any]:
    return {
        "id": change.id,
        "method": change.method,
        "deposit_rands": change.deposit_rands,
        "proposed_by_me": change.proposed_by == viewer.id,
        "created_at": change.created_at.isoformat(),
    }


def payment_view(session: Session, job: Job, viewer: Customer | Provider) -> dict[str, Any]:
    """Everything the job page shows about paying: the plan, what's due now, a change waiting
    for an answer, and receipts. Both sides see the same, except who asked for the change."""
    plan = read_plan(session, job.id)
    payments = list_payments(session, job.id)
    paid_rands = sum_paid_rands(payments)
    due = find_amount_due(job, plan, paid_rands)
    change = read_pending_change(session, job.id) if plan else None
    return {
        "plan": None
        if plan is None
        else {
            "method": plan.method,
            "total_rands": plan.total_rands,
            "deposit_rands": plan.deposit_rands,
            "agreed_at": plan.agreed_at.isoformat(),
        },
        "paid_rands": paid_rands,
        "due": None if due is None else {"kind": due.kind, "amount_rands": due.amount_rands},
        "can_change": can_change_plan(job, plan, paid_rands),
        "change": None if change is None else change_view(change, viewer),
        "receipts": [receipt_view(payment) for payment in payments if payment.state == PAID],
    }


def create_change(
    session: Session, job: Job, proposer: Customer | Provider, method: str, deposit: int | None
) -> PaymentPlanChange:
    """Asks the other side to change how the job is paid. Refused once work has started or money
    has moved (409 plan_locked), while another change waits for an answer (409
    change_pending), or when nothing would change (422 same_plan). The caller commits."""
    plan = read_plan(session, job.id)
    if not can_change_plan(job, plan, sum_paid_rands(list_payments(session, job.id))):
        raise refuse(409, "plan_locked", "The payment plan can't change any more")
    if read_pending_change(session, job.id) is not None:
        raise refuse(409, "change_pending", "Another change is waiting for an answer")
    deposit_rands = check_deposit(method, deposit, plan.total_rands)
    if (method, deposit_rands) == (plan.method, plan.deposit_rands):
        raise refuse(422, "same_plan", "That's already the plan")
    change = PaymentPlanChange(
        id=f"change_{uuid.uuid4().hex[:10]}",
        job_id=job.id,
        proposed_by=proposer.id,
        method=method,
        deposit_rands=deposit_rands,
        state=PENDING,
        created_at=now(),
    )
    session.add(change)
    return change


def find_pending_change(session: Session, job_id: str, change_id: str) -> PaymentPlanChange:
    change = session.get(PaymentPlanChange, change_id)
    if change is None or change.job_id != job_id or change.state != PENDING:
        raise refuse(404, "change_not_found", "That change isn't waiting for an answer")
    return change


def update_plan_from_change(
    session: Session, job: Job, change: PaymentPlanChange, answerer: Customer | Provider
) -> None:
    """The other side agrees: the plan becomes what the change asked for. The asker can't agree
    to their own change (403), and a job that has started since is refused (409 plan_locked).
    Unfinished checkouts are cancelled, since their amount may be wrong now. Caller commits."""
    if change.proposed_by == answerer.id:
        raise refuse(403, "own_change", "The other side has to agree to this")
    plan = read_plan(session, job.id)
    if not can_change_plan(job, plan, sum_paid_rands(list_payments(session, job.id))):
        raise refuse(409, "plan_locked", "The payment plan can't change any more")
    plan.method, plan.deposit_rands, plan.agreed_at = change.method, change.deposit_rands, now()
    change.state, change.decided_at = AGREED, now()
    cancel_pending_payments(session, job.id)
    session.add_all([plan, change])


def delete_change(change: PaymentPlanChange, answerer: Customer | Provider) -> str:
    """Says no to a change: the other side declines it, or the asker withdraws it. The plan
    stays as it was. Returns the new state. The caller adds and commits."""
    change.state = WITHDRAWN if change.proposed_by == answerer.id else DECLINED
    change.decided_at = now()
    return change.state
