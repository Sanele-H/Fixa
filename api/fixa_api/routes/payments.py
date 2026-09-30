"""Paying for a job: the agreed plan, changing it (both must agree), paying in the app, and the
payment company's webhook. The rules are in payment_plans.py, the payment companies in
payment_providers.py.

Only the job's customer and its picked provider can see or change a job's payment (404 for
anyone else, like the job itself). Only the customer pays.
"""

import datetime as dt
import html
import logging
import os
import uuid
from typing import Annotated, Literal
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from fixa_api import payment_plans as plans
from fixa_api.auth import current_user, require_role
from fixa_api.db import get_session
from fixa_api.job_views import is_job_customer, is_job_provider
from fixa_api.models import Customer, Job, Payment, Provider
from fixa_api.notifications import notify
from fixa_api.payment_providers import (
    PAYFAST_NOTIFY_PATH,
    CheckoutRequest,
    MockPaymentProvider,
    PaymentNotice,
    PaymentNoticeError,
    PaymentProvider,
    format_rands,
    get_payment_provider,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["payments"])

User = Annotated[Customer | Provider, Depends(current_user)]
CustomerUser = Annotated[Customer, Depends(require_role("customer"))]
DbSession = Annotated[Session, Depends(get_session)]
Payments = Annotated[PaymentProvider, Depends(get_payment_provider)]
PaymentMethod = Literal["in_app_after", "in_app_split", "cash"]

SEE_OTHER = 303  # after a form POST, the browser GETs the next page
CENTS_PER_RAND = 100


class NewPlanChange(BaseModel):
    """A change to how the job is paid. deposit_rands only for in_app_split."""

    method: PaymentMethod
    deposit_rands: int | None = Field(default=None, gt=0)


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def find_party_job(session: Session, job_id: str, user: Customer | Provider) -> Job:
    """The job, for its customer or its picked provider; 404 for anyone else."""
    job = session.get(Job, job_id)
    if job is None or not (is_job_customer(job, user) or is_job_provider(job, user)):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def find_other_party(session: Session, job: Job, user: Customer | Provider):
    """The person on the other side of the job from user."""
    if user.role == "customer":
        return session.get(Provider, job.provider_id)
    return session.get(Customer, job.customer_id)


def read_base_url(request: Request, setting: str) -> str:
    """Where links back to us start: PUBLIC_APP_URL or PUBLIC_API_URL when set (needed live, so
    PayFast can reach the webhook), else the address this request came in on."""
    return (os.environ.get(setting) or str(request.base_url)).rstrip("/")


@router.get("/jobs/{job_id}/payment")
def read_payment(job_id: str, user: User, session: DbSession):
    """The plan, what's due now, any change waiting for an answer, and receipts."""
    job = find_party_job(session, job_id, user)
    return plans.payment_view(session, job, user)


@router.post("/jobs/{job_id}/payment/changes", status_code=201)
def create_plan_change(job_id: str, body: NewPlanChange, user: User, session: DbSession):
    """Ask the other side to pay a different way. Nothing changes until they agree."""
    job = find_party_job(session, job_id, user)
    plans.create_change(session, job, user, body.method, body.deposit_rands)
    session.commit()
    notify(
        session,
        find_other_party(session, job, user),
        "payment_change_asked",
        job.id,
        name=user.display_name,
    )
    return plans.payment_view(session, job, user)


@router.post("/jobs/{job_id}/payment/changes/{change_id}/agree")
def agree_plan_change(job_id: str, change_id: str, user: User, session: DbSession):
    """The other side agrees, and the plan becomes the change."""
    job = find_party_job(session, job_id, user)
    change = plans.find_pending_change(session, job.id, change_id)
    plans.update_plan_from_change(session, job, change, user)
    session.commit()
    notify(
        session,
        find_other_party(session, job, user),
        "payment_change_agreed",
        job.id,
        name=user.display_name,
    )
    return plans.payment_view(session, job, user)


@router.post("/jobs/{job_id}/payment/changes/{change_id}/decline")
def decline_plan_change(job_id: str, change_id: str, user: User, session: DbSession):
    """The other side says no, or the asker takes it back. The plan stays as it was."""
    job = find_party_job(session, job_id, user)
    change = plans.find_pending_change(session, job.id, change_id)
    new_state = plans.delete_change(change, user)
    session.add(change)
    session.commit()
    if new_state == plans.DECLINED:
        notify(
            session,
            find_other_party(session, job, user),
            "payment_change_declined",
            job.id,
            name=user.display_name,
        )
    return plans.payment_view(session, job, user)


def create_payment(session: Session, job: Job, due: plans.AmountDue, gateway: str) -> Payment:
    """A pending payment for what's due. Earlier unfinished checkouts are cancelled first, so
    only one can ever be paid. The id is long and random: the mock checkout page is opened by
    link, without the login token."""
    plans.cancel_pending_payments(session, job.id)
    payment = Payment(
        id=f"pay_{uuid.uuid4().hex[:20]}",
        job_id=job.id,
        kind=due.kind,
        amount_rands=due.amount_rands,
        state=plans.PENDING,
        gateway=gateway,
        created_at=now(),
    )
    session.add(payment)
    session.commit()
    return payment


@router.post("/jobs/{job_id}/payments", status_code=201)
def start_payment(
    job_id: str,
    request: Request,
    customer: CustomerUser,
    session: DbSession,
    payment_provider: Payments,
):
    """Start paying what's due now (the deposit, or the rest after "It's done"). Answers where to
    send the browser: the payment company's hosted page. 409 nothing_due when there's nothing to
    pay in the app right now."""
    job = find_party_job(session, job_id, customer)
    plan = plans.read_plan(session, job.id)
    paid_rands = plans.sum_paid_rands(plans.list_payments(session, job.id))
    due = plans.find_amount_due(job, plan, paid_rands)
    if due is None:
        raise plans.refuse(409, "nothing_due", "There's nothing to pay in the app right now")
    payment = create_payment(session, job, due, payment_provider.name)
    app_url, api_url = (
        read_base_url(request, "PUBLIC_APP_URL"),
        read_base_url(request, "PUBLIC_API_URL"),
    )
    job_page_url = f"{app_url}/jobs/{job.id}"
    checkout = payment_provider.create_checkout(
        CheckoutRequest(
            payment_id=payment.id,
            amount_rands=payment.amount_rands,
            item_name=f"Fixa {job.trade} job, {payment.kind}",
            return_url=f"{job_page_url}?payment={payment.id}",
            cancel_url=f"{job_page_url}?payment_cancelled={payment.id}",
            notify_url=f"{api_url}{PAYFAST_NOTIFY_PATH}",
        )
    )
    return {
        "payment_id": payment.id,
        "checkout_url": checkout.url,
        "method": checkout.method,
        "fields": checkout.fields,
    }


def confirm_payment(session: Session, notice: PaymentNotice) -> None:
    """Counts a checked notice. Idempotent: a payment company may send the same notice twice.
    The amount must match to the cent, and a cancelled payment (the plan changed while the
    customer was on the checkout page) isn't counted; both are logged for the team."""
    payment = session.get(Payment, notice.payment_id)
    if payment is None or payment.state == plans.PAID:
        return
    if payment.state != plans.PENDING:
        logger.warning("Payment %s was %s when its notice came", payment.id, payment.state)
        return
    if not notice.paid:
        payment.state = plans.CANCELLED
    elif notice.amount_cents != payment.amount_rands * CENTS_PER_RAND:
        logger.warning("Payment %s: the notice's amount doesn't match", payment.id)
        payment.state = plans.FAILED
    else:
        payment.state, payment.paid_at = plans.PAID, now()
        payment.gateway_reference = notice.reference
    session.add(payment)
    session.commit()
    if payment.state == plans.PAID:
        tell_both_about_payment(session, payment)


def tell_both_about_payment(session: Session, payment: Payment) -> None:
    """The provider hears the money came in; the customer gets their receipt in the inbox."""
    job = session.get(Job, payment.job_id)
    customer = session.get(Customer, job.customer_id)
    provider = session.get(Provider, job.provider_id) if job.provider_id else None
    amount = payment.amount_rands
    notify(session, provider, "payment_received", job.id, name=customer.display_name, amount=amount)
    notify(session, customer, "payment_receipt", job.id, amount=amount)


@router.post("/payments/payfast/notify")
async def receive_payfast_notice(request: Request, session: DbSession, payment_provider: Payments):
    """PayFast's ITN webhook. The raw body is read as-is, since the signature is over the fields
    in the order PayFast sent them. Answers 200 to a genuine notice, so PayFast stops resending,
    and 400 to anything else."""
    if payment_provider.name != "payfast":
        raise HTTPException(status_code=404, detail="Not found")
    fields = parse_qsl((await request.body()).decode(), keep_blank_values=True)
    try:
        notice = await run_in_threadpool(payment_provider.read_notice, fields)
    except PaymentNoticeError as problem:
        logger.warning("PayFast notice refused: %s", problem)
        raise HTTPException(status_code=400, detail="Notice refused") from None
    await run_in_threadpool(confirm_payment, session, notice)
    return PlainTextResponse("OK")


# --- The mock payment company's hosted checkout page. It's server-rendered like a real one, so
# the app hands off and comes back the same way it would with PayFast.

MOCK_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test checkout</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #e7e7e4; color: #101010; margin: 0;
         padding: 24px 16px; }}
  main {{ max-width: 420px; margin: 0 auto; background: #fff; border-radius: 20px;
          padding: 24px; }}
  .note {{ background: #fdf0cc; color: #5c4300; border-radius: 12px; padding: 12px;
           font-size: 14px; }}
  .amount {{ font-size: 40px; font-weight: 500; margin: 16px 0; }}
  button {{ width: 100%; min-height: 48px; border-radius: 999px; font-size: 16px;
            margin-top: 12px; border: 1px solid #111; cursor: pointer; }}
  .pay {{ background: #111; color: #fff; }}
  .cancel {{ background: #fff; color: #111; }}
</style></head>
<body><main>
  <p class="note">Test checkout. No card is needed and no money moves.</p>
  <p>{item}</p>
  <p class="amount">R{amount}</p>
  <form method="post">
    <button class="pay" name="paid" value="yes">Pay R{amount}</button>
    <button class="cancel" name="paid" value="no">Cancel</button>
  </form>
</main></body></html>"""

MOCK_DONE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Test checkout</title></head>
<body style="font-family: system-ui, sans-serif; padding: 24px">
<p>This payment is {state}.</p><p><a href="/jobs/{job_id}">Back to the job</a></p>
</body></html>"""


def find_mock_payment(session: Session, payment_id: str) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None or payment.gateway != MockPaymentProvider.name:
        raise HTTPException(status_code=404, detail="Not found")
    return payment


@router.get("/payments/mock/{payment_id}", response_class=HTMLResponse)
def read_mock_checkout(payment_id: str, session: DbSession):
    """The test checkout page, opened by link (no login token), like a real hosted page."""
    payment = find_mock_payment(session, payment_id)
    if payment.state != plans.PENDING:
        return HTMLResponse(MOCK_DONE_PAGE.format(state=payment.state, job_id=payment.job_id))
    job = session.get(Job, payment.job_id)
    return HTMLResponse(
        MOCK_PAGE.format(
            item=html.escape(f"Fixa {job.trade} job, {payment.kind}"),
            amount=format_rands(payment.amount_rands),
        )
    )


@router.post("/payments/mock/{payment_id}")
async def submit_mock_checkout(payment_id: str, request: Request, session: DbSession):
    """Pay or cancel on the test page. The result goes through confirm_payment, the same code a
    real webhook reaches, then the browser goes back to the job page, as with PayFast."""
    payment = await run_in_threadpool(find_mock_payment, session, payment_id)
    form = parse_qsl((await request.body()).decode(), keep_blank_values=True)
    paid = dict(form).get("paid") == "yes"
    notice = MockPaymentProvider().read_notice(
        [
            ("payment_id", payment.id),
            ("paid", "yes" if paid else "no"),
            ("amount", format_rands(payment.amount_rands)),
        ]
    )
    await run_in_threadpool(confirm_payment, session, notice)
    result = "payment" if paid else "payment_cancelled"
    return RedirectResponse(f"/jobs/{payment.job_id}?{result}={payment.id}", status_code=SEE_OTHER)
