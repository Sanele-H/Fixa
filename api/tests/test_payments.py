"""Agreeing how a job is paid, changing it, and paying in the app (mock and PayFast)."""

import hashlib
from urllib.parse import urlsplit

import httpx
import pytest
from sqlmodel import select

from fixa_api.main import app
from fixa_api.models import Notification, Payment
from fixa_api.payment_providers import (
    CheckoutRequest,
    PayFastPaymentProvider,
    PaymentNotice,
    PaymentNoticeError,
    build_param_string,
    encode_param,
    get_payment_provider,
    sign,
)
from fixa_api.routes.payments import confirm_payment

LINDIWE = "082 000 0001"  # cust_001
PLUMBER = "071 000 0001"  # prov_001
OTHER_PLUMBER = "071 000 0002"  # prov_002
QUOTE_TIME = "2026-10-01T10:00:00+02:00"
PRICE = 400


# --- Walking a job, as each side


def post_job(client, headers) -> str:
    body = {
        "description": "My geyser is leaking through the ceiling",
        "lang": "en",
        "trade": "plumbing",
        "urgency": "urgent",
        "size": "small",
        "suburb": "Braamfontein",
    }
    return client.post("/api/jobs", json=body, headers=headers).json()["id"]


def send_quote(client, headers, job_id, **changes):
    body = {"amount_rands": PRICE, "when": QUOTE_TIME} | changes
    return client.post(f"/api/jobs/{job_id}/quotes", json=body, headers=headers)


def accept(client, headers, quote_id, method=None):
    body = None if method is None else {"payment_method": method}
    return client.post(f"/api/quotes/{quote_id}/accept", json=body, headers=headers)


def read_payment(client, headers, job_id):
    return client.get(f"/api/jobs/{job_id}/payment", headers=headers).json()


@pytest.fixture
def lindiwe(log_in):
    return log_in(LINDIWE)


@pytest.fixture
def plumber(log_in):
    return log_in(PLUMBER)


@pytest.fixture
def make_accepted_job(seeded_client, lindiwe, plumber):
    """make_accepted_job("in_app_split") posts, quotes (offering all three ways, R200 deposit)
    and accepts with that way. Returns the job id."""

    def make(method: str) -> str:
        job_id = post_job(seeded_client, lindiwe)
        quote = send_quote(
            seeded_client,
            plumber,
            job_id,
            payment_methods=["in_app_after", "in_app_split", "cash"],
            deposit_rands=200,
        ).json()
        assert accept(seeded_client, lindiwe, quote["id"], method).status_code == 200
        return job_id

    return make


@pytest.fixture
def make_confirmed_job(seeded_client, plumber, make_accepted_job):
    def make(method: str) -> str:
        job_id = make_accepted_job(method)
        seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)
        return job_id

    return make


def finish(client, lindiwe, plumber, job_id):
    client.post(f"/api/jobs/{job_id}/check-in", headers=plumber)
    client.post(f"/api/jobs/{job_id}/done", json={"completed": True}, headers=lindiwe)


def pay_on_test_checkout(client, lindiwe, job_id, paid=True):
    """Starts paying what's due, and pays (or cancels) on the test checkout page."""
    checkout = client.post(f"/api/jobs/{job_id}/payments", headers=lindiwe).json()
    assert checkout["method"] == "GET"
    page = client.get(checkout["checkout_url"])
    assert page.status_code == 200 and "Test checkout" in page.text
    return client.post(
        checkout["checkout_url"], data={"paid": "yes" if paid else "no"}, follow_redirects=False
    )


# --- Feature 4: the quote's ways to pay, and the plan


def test_a_quote_accepts_paying_in_the_app_after_or_cash_by_default(
    seeded_client, lindiwe, plumber
):
    job_id = post_job(seeded_client, lindiwe)
    quote = send_quote(seeded_client, plumber, job_id).json()
    assert quote["payment_methods"] == ["in_app_after", "cash"]
    assert quote["deposit_rands"] is None


def test_a_split_quote_needs_a_deposit_of_at_most_half(seeded_client, lindiwe, plumber):
    job_id = post_job(seeded_client, lindiwe)
    split = {"payment_methods": ["in_app_split"]}
    missing = send_quote(seeded_client, plumber, job_id, **split)
    too_high = send_quote(seeded_client, plumber, job_id, **split, deposit_rands=PRICE // 2 + 1)
    at_half = send_quote(seeded_client, plumber, job_id, **split, deposit_rands=PRICE // 2)
    assert missing.json()["detail"]["error"] == "deposit_required"
    assert too_high.json()["detail"]["error"] == "deposit_too_high"
    assert at_half.status_code == 201
    assert at_half.json()["deposit_rands"] == PRICE // 2


def test_a_deposit_without_a_split_is_ignored(seeded_client, lindiwe, plumber):
    job_id = post_job(seeded_client, lindiwe)
    quote = send_quote(seeded_client, plumber, job_id, payment_methods=["cash"], deposit_rands=50)
    assert quote.json()["deposit_rands"] is None


def test_the_customer_picks_a_way_to_pay_when_accepting(seeded_client, lindiwe, make_accepted_job):
    job_id = make_accepted_job("in_app_split")
    plan = read_payment(seeded_client, lindiwe, job_id)["plan"]
    assert plan["method"] == "in_app_split"
    assert (plan["total_rands"], plan["deposit_rands"]) == (PRICE, 200)


def test_accepting_without_a_way_to_pay_takes_the_quotes_first(seeded_client, lindiwe, plumber):
    job_id = post_job(seeded_client, lindiwe)
    quote = send_quote(seeded_client, plumber, job_id, payment_methods=["cash"]).json()
    accept(seeded_client, lindiwe, quote["id"])
    assert read_payment(seeded_client, lindiwe, job_id)["plan"]["method"] == "cash"


def test_a_way_to_pay_the_quote_doesnt_offer_is_refused(seeded_client, lindiwe, plumber):
    job_id = post_job(seeded_client, lindiwe)
    quote = send_quote(seeded_client, plumber, job_id, payment_methods=["cash"]).json()
    response = accept(seeded_client, lindiwe, quote["id"], "in_app_after")
    assert response.json()["detail"]["error"] == "payment_method_not_offered"
    assert seeded_client.get(f"/api/jobs/{job_id}", headers=lindiwe).json()["state"] == "quoting"


def test_a_decline_drops_the_plan(seeded_client, lindiwe, plumber, make_accepted_job):
    job_id = make_accepted_job("cash")
    seeded_client.post(f"/api/jobs/{job_id}/decline", headers=plumber)
    other = send_quote(seeded_client, plumber, job_id).json()
    accept(seeded_client, lindiwe, other["id"], "in_app_after")
    assert read_payment(seeded_client, lindiwe, job_id)["plan"]["method"] == "in_app_after"


def test_only_the_jobs_two_people_see_its_payment(
    seeded_client, log_in, lindiwe, make_accepted_job
):
    job_id = make_accepted_job("cash")
    response = seeded_client.get(f"/api/jobs/{job_id}/payment", headers=log_in(OTHER_PLUMBER))
    assert response.status_code == 404


# --- Feature 4: changing the plan, when both agree


def ask_change(client, headers, job_id, method, deposit_rands=None):
    body = {"method": method, "deposit_rands": deposit_rands}
    return client.post(f"/api/jobs/{job_id}/payment/changes", json=body, headers=headers)


def answer_change(client, headers, job_id, answer):
    change_id = read_payment(client, headers, job_id)["change"]["id"]
    return client.post(f"/api/jobs/{job_id}/payment/changes/{change_id}/{answer}", headers=headers)


def test_a_change_takes_effect_only_when_the_other_side_agrees(
    seeded_client, seeded_session, lindiwe, plumber, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_after")
    asked = ask_change(seeded_client, lindiwe, job_id, "cash").json()
    assert asked["plan"]["method"] == "in_app_after"
    assert asked["change"]["proposed_by_me"] is True
    assert read_payment(seeded_client, plumber, job_id)["change"]["proposed_by_me"] is False

    agreed = answer_change(seeded_client, plumber, job_id, "agree").json()
    assert agreed["plan"]["method"] == "cash"
    assert agreed["change"] is None
    kinds = {note.kind for note in seeded_session.exec(select(Notification))}
    assert {"payment_change_asked", "payment_change_agreed"} <= kinds


def test_nobody_agrees_to_their_own_change(seeded_client, lindiwe, make_confirmed_job):
    job_id = make_confirmed_job("in_app_after")
    ask_change(seeded_client, lindiwe, job_id, "cash")
    response = answer_change(seeded_client, lindiwe, job_id, "agree")
    assert response.status_code == 403


def test_declining_keeps_the_plan_and_the_asker_can_withdraw(
    seeded_client, lindiwe, plumber, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_after")
    ask_change(seeded_client, lindiwe, job_id, "cash")
    declined = answer_change(seeded_client, plumber, job_id, "decline").json()
    assert declined["plan"]["method"] == "in_app_after" and declined["change"] is None

    ask_change(seeded_client, plumber, job_id, "cash")
    withdrawn = answer_change(seeded_client, plumber, job_id, "decline").json()
    assert withdrawn["change"] is None


def test_one_change_at_a_time_and_it_must_change_something(
    seeded_client, lindiwe, plumber, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_after")
    same = ask_change(seeded_client, lindiwe, job_id, "in_app_after")
    assert same.json()["detail"]["error"] == "same_plan"
    ask_change(seeded_client, lindiwe, job_id, "cash")
    second = ask_change(seeded_client, plumber, job_id, "in_app_split", 100)
    assert second.json()["detail"]["error"] == "change_pending"


def test_a_changed_deposit_is_capped_at_half(seeded_client, lindiwe, make_confirmed_job):
    job_id = make_confirmed_job("in_app_after")
    response = ask_change(seeded_client, lindiwe, job_id, "in_app_split", PRICE // 2 + 1)
    assert response.json()["detail"]["error"] == "deposit_too_high"


def test_the_plan_is_locked_once_work_starts(seeded_client, lindiwe, plumber, make_confirmed_job):
    job_id = make_confirmed_job("in_app_after")
    ask_change(seeded_client, lindiwe, job_id, "cash")
    seeded_client.post(f"/api/jobs/{job_id}/check-in", headers=plumber)
    assert read_payment(seeded_client, lindiwe, job_id)["can_change"] is False
    agreeing = answer_change(seeded_client, plumber, job_id, "agree")
    assert agreeing.json()["detail"]["error"] == "plan_locked"


def test_the_plan_is_locked_once_money_has_moved(seeded_client, lindiwe, make_confirmed_job):
    job_id = make_confirmed_job("in_app_split")
    pay_on_test_checkout(seeded_client, lindiwe, job_id)
    response = ask_change(seeded_client, lindiwe, job_id, "cash")
    assert response.json()["detail"]["error"] == "plan_locked"


# --- Feature 5: paying in the app, on the test checkout


def test_a_split_plan_asks_for_the_deposit_on_confirm_and_the_rest_at_done(
    seeded_client, lindiwe, plumber, make_accepted_job
):
    job_id = make_accepted_job("in_app_split")
    assert read_payment(seeded_client, lindiwe, job_id)["due"] is None  # not confirmed yet

    seeded_client.post(f"/api/jobs/{job_id}/confirm", headers=plumber)
    assert read_payment(seeded_client, lindiwe, job_id)["due"] == {
        "kind": "deposit",
        "amount_rands": 200,
    }
    redirect = pay_on_test_checkout(seeded_client, lindiwe, job_id)
    assert redirect.status_code == 303
    assert urlsplit(redirect.headers["location"]).path == f"/jobs/{job_id}"
    after_deposit = read_payment(seeded_client, lindiwe, job_id)
    assert (after_deposit["paid_rands"], after_deposit["due"]) == (200, None)

    finish(seeded_client, lindiwe, plumber, job_id)
    assert read_payment(seeded_client, lindiwe, job_id)["due"] == {
        "kind": "balance",
        "amount_rands": PRICE - 200,
    }
    pay_on_test_checkout(seeded_client, lindiwe, job_id)
    receipts = read_payment(seeded_client, plumber, job_id)["receipts"]
    assert [(r["kind"], r["amount_rands"]) for r in receipts] == [
        ("deposit", 200),
        ("balance", 200),
    ]
    assert all(r["reference"].startswith("MOCK-") for r in receipts)


def test_paying_after_asks_for_everything_at_done(
    seeded_client, lindiwe, plumber, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_after")
    assert read_payment(seeded_client, lindiwe, job_id)["due"] is None
    finish(seeded_client, lindiwe, plumber, job_id)
    assert read_payment(seeded_client, lindiwe, job_id)["due"] == {
        "kind": "full",
        "amount_rands": PRICE,
    }


def test_nothing_is_paid_in_the_app_for_cash(seeded_client, lindiwe, plumber, make_confirmed_job):
    job_id = make_confirmed_job("cash")
    finish(seeded_client, lindiwe, plumber, job_id)
    response = seeded_client.post(f"/api/jobs/{job_id}/payments", headers=lindiwe)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "nothing_due"


def test_cancelling_on_the_checkout_leaves_the_amount_due(
    seeded_client, lindiwe, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_split")
    pay_on_test_checkout(seeded_client, lindiwe, job_id, paid=False)
    payment = read_payment(seeded_client, lindiwe, job_id)
    assert payment["receipts"] == []
    assert payment["due"]["kind"] == "deposit"


def test_only_the_customer_pays(seeded_client, plumber, make_confirmed_job):
    job_id = make_confirmed_job("in_app_split")
    assert seeded_client.post(f"/api/jobs/{job_id}/payments", headers=plumber).status_code == 403


def test_the_provider_hears_about_the_money_and_the_customer_gets_a_receipt(
    seeded_client, seeded_session, lindiwe, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_split")
    pay_on_test_checkout(seeded_client, lindiwe, job_id)
    notes = {(n.user_id, n.kind) for n in seeded_session.exec(select(Notification))}
    assert {("prov_001", "payment_received"), ("cust_001", "payment_receipt")} <= notes


def start_deposit(client, lindiwe, job_id) -> str:
    payment_id = client.post(f"/api/jobs/{job_id}/payments", headers=lindiwe).json()["payment_id"]
    return payment_id


def test_a_notice_counts_once_and_only_for_the_right_amount(
    seeded_client, seeded_session, lindiwe, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_split")
    payment_id = start_deposit(seeded_client, lindiwe, job_id)
    wrong = PaymentNotice(payment_id=payment_id, paid=True, amount_cents=100, reference="x")
    confirm_payment(seeded_session, wrong)
    assert seeded_session.get(Payment, payment_id).state == "failed"

    payment_id = start_deposit(seeded_client, lindiwe, job_id)
    right = PaymentNotice(payment_id=payment_id, paid=True, amount_cents=20_000, reference="y")
    confirm_payment(seeded_session, right)
    confirm_payment(seeded_session, right)  # sent twice
    assert read_payment(seeded_client, lindiwe, job_id)["paid_rands"] == 200


def test_a_new_checkout_cancels_the_unfinished_one(
    seeded_client, seeded_session, lindiwe, make_confirmed_job
):
    job_id = make_confirmed_job("in_app_split")
    first = start_deposit(seeded_client, lindiwe, job_id)
    start_deposit(seeded_client, lindiwe, job_id)
    late = PaymentNotice(payment_id=first, paid=True, amount_cents=20_000, reference="late")
    confirm_payment(seeded_session, late)
    assert seeded_session.get(Payment, first).state == "cancelled"
    assert read_payment(seeded_client, lindiwe, job_id)["paid_rands"] == 0


# --- Feature 5: PayFast, with its servers replaced

MERCHANT_ID, MERCHANT_KEY, PASSPHRASE = "10000100", "46f0cd694581a", "test passphrase"


def fake_payfast(answer: str = "VALID", seen: list | None = None) -> PayFastPaymentProvider:
    def validate(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, text=answer)

    client = httpx.Client(transport=httpx.MockTransport(validate))
    return PayFastPaymentProvider(MERCHANT_ID, MERCHANT_KEY, PASSPHRASE, True, client)


def payfast_notice_fields(payment_id: str, amount: str, passphrase=PASSPHRASE):
    """An ITN as PayFast sends it: its fields in order, empty ones included, signed last."""
    fields = [
        ("m_payment_id", payment_id),
        ("pf_payment_id", "1089250"),
        ("payment_status", "COMPLETE"),
        ("item_name", "Fixa plumbing job, deposit"),
        ("item_description", ""),
        ("amount_gross", amount),
        ("amount_fee", "-4.60"),
        ("amount_net", "195.40"),
        ("name_first", "Test"),
        ("merchant_id", MERCHANT_ID),
    ]
    return [*fields, ("signature", sign(build_param_string(fields, False), passphrase))]


def encode_form(fields) -> str:
    return "&".join(f"{name}={encode_param(value)}" for name, value in fields)


def test_payfast_signs_like_php_urlencode():
    fields = [("merchant_id", "10000100"), ("return_url", "https://x.co/jobs/1?a=b c~")]
    expected_text = (
        "merchant_id=10000100&return_url=https%3A%2F%2Fx.co%2Fjobs%2F1%3Fa%3Db+c%7E"
        "&passphrase=test+passphrase"
    )
    assert sign(build_param_string(fields, True), PASSPHRASE) == (
        hashlib.md5(expected_text.encode()).hexdigest()
    )


def test_payfast_checkout_is_a_signed_form_to_the_sandbox():
    checkout = fake_payfast().create_checkout(
        CheckoutRequest("pay_1", 200, "Fixa job", "https://a/r", "https://a/c", "https://b/n")
    )
    assert checkout.url == "https://sandbox.payfast.co.za/eng/process"
    assert checkout.method == "POST"
    assert checkout.fields["amount"] == "200.00"
    unsigned = [(k, v) for k, v in checkout.fields.items() if k != "signature"]
    assert checkout.fields["signature"] == sign(build_param_string(unsigned, True), PASSPHRASE)


def test_a_genuine_payfast_notice_is_read_and_checked_with_payfast():
    seen: list[httpx.Request] = []
    notice = fake_payfast(seen=seen).read_notice(payfast_notice_fields("pay_1", "200.00"))
    assert notice == PaymentNotice("pay_1", True, 20_000, "1089250")
    assert seen[0].url.path == "/eng/query/validate"
    assert b"signature" not in seen[0].content


def test_a_payfast_notice_with_a_wrong_signature_is_refused():
    fields = payfast_notice_fields("pay_1", "200.00", passphrase="guessed")
    with pytest.raises(PaymentNoticeError, match="signature"):
        fake_payfast().read_notice(fields)


def test_a_payfast_notice_payfast_doesnt_vouch_for_is_refused():
    with pytest.raises(PaymentNoticeError, match="isn't valid"):
        fake_payfast(answer="INVALID").read_notice(payfast_notice_fields("pay_1", "200.00"))


def test_paying_through_payfast_end_to_end(seeded_client, lindiwe, make_confirmed_job):
    job_id = make_confirmed_job("in_app_split")
    app.dependency_overrides[get_payment_provider] = fake_payfast
    checkout = seeded_client.post(f"/api/jobs/{job_id}/payments", headers=lindiwe).json()
    assert checkout["method"] == "POST"
    assert checkout["fields"]["notify_url"].endswith("/api/payments/payfast/notify")

    fields = payfast_notice_fields(checkout["payment_id"], "200.00")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    notice_url = "/api/payments/payfast/notify"
    forged = [*fields[:-1], ("signature", "0" * 32)]
    assert seeded_client.post(notice_url, content=encode_form(forged), headers=headers).is_error
    response = seeded_client.post(notice_url, content=encode_form(fields), headers=headers)
    assert response.status_code == 200
    receipts = read_payment(seeded_client, lindiwe, job_id)["receipts"]
    assert [(r["gateway"], r["reference"]) for r in receipts] == [("payfast", "1089250")]


def test_the_payfast_webhook_is_off_when_payfast_isnt_used(seeded_client):
    assert seeded_client.post("/api/payments/payfast/notify", content="a=b").status_code == 404
