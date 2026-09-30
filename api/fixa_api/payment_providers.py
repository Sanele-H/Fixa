"""The payment companies that take a customer's card, behind one interface.

(A "payment provider" here is a payment company, not a Fixa service provider.)

Card details never reach Fixa. The app sends the customer to the payment company's own hosted
checkout page; the company then tells our server the result (a webhook), which we check before
counting the money. Two implementations:

- MockPaymentProvider (PAYMENT_PROVIDER=mock, the default): our own test checkout page, no keys,
  no real money. For the demo and the tests.
- PayFastPaymentProvider (PAYMENT_PROVIDER=payfast): PayFast's sandbox, or live.

Why PayFast for the real one: it's South African and settles in rands; besides cards its hosted
page offers Instant EFT and QR payments, which matter for customers without a credit card; its
sandbox is free with test merchant details, so it works without registering a business; and
its webhook (ITN) is signed and can be checked back with PayFast's own server.
"""

import hashlib
import hmac
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

MOCK_CHECKOUT_PATH = "/api/payments/mock/{payment_id}"
PAYFAST_NOTIFY_PATH = "/api/payments/payfast/notify"
PAYFAST_SANDBOX_HOST = "https://sandbox.payfast.co.za"
PAYFAST_LIVE_HOST = "https://www.payfast.co.za"
PAYFAST_PROCESS_PATH = "/eng/process"
PAYFAST_VALIDATE_PATH = "/eng/query/validate"
PAYFAST_COMPLETE_STATUS = "COMPLETE"
PAYFAST_VALID_ANSWER = "VALID"
REQUEST_TIMEOUT_SECONDS = 10
CENTS_PER_RAND = 100


@dataclass(frozen=True)
class CheckoutRequest:
    """What one payment is for, and where the customer's browser and the webhook go after."""

    payment_id: str
    amount_rands: int
    item_name: str
    return_url: str  # the job page, after paying
    cancel_url: str  # the job page, after giving up
    notify_url: str  # our webhook


@dataclass(frozen=True)
class Checkout:
    """Where to send the customer's browser: open url with GET, or submit fields to it with POST
    (a hosted checkout that needs a signed form, like PayFast's)."""

    url: str
    method: str = "GET"
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentNotice:
    """A webhook the provider sent, once checked. paid is False for a failed or cancelled card."""

    payment_id: str
    paid: bool
    amount_cents: int
    reference: str


class PaymentNoticeError(Exception):
    """A webhook that isn't genuine: wrong signature, wrong merchant, or the provider's own server
    didn't confirm it. Nothing is counted."""


class PaymentProvider(Protocol):
    name: str

    def create_checkout(self, request: CheckoutRequest) -> Checkout:
        """Where the customer pays for this payment, on the provider's hosted page."""

    def read_notice(self, fields: Sequence[tuple[str, str]]) -> PaymentNotice:
        """Checks a webhook's form fields (in the order received) and says what happened. Raises
        PaymentNoticeError when it isn't genuine."""


def format_rands(amount_rands: int) -> str:
    """ "450.00": the amount format payment forms use."""
    return f"{amount_rands:.2f}"


class MockPaymentProvider:
    """A pretend payment company: its checkout page is ours (routes/payments.py), and paying there
    sends the notice straight to the same code a real webhook reaches. No card, no money."""

    name = "mock"

    def create_checkout(self, request: CheckoutRequest) -> Checkout:
        return Checkout(url=MOCK_CHECKOUT_PATH.format(payment_id=request.payment_id))

    def read_notice(self, fields: Sequence[tuple[str, str]]) -> PaymentNotice:
        """The mock page's own form: payment_id, paid ("yes"/"no") and amount in rands."""
        values = dict(fields)
        return PaymentNotice(
            payment_id=values["payment_id"],
            paid=values.get("paid") == "yes",
            amount_cents=round(float(values["amount"]) * CENTS_PER_RAND),
            reference=f"MOCK-{values['payment_id'].removeprefix('pay_').upper()}",
        )


def encode_param(value: str) -> str:
    """PHP's urlencode, which PayFast signs with: spaces as +, and ~ encoded too."""
    return quote_plus(value.strip(), safe="").replace("~", "%7E")


def build_param_string(fields: Sequence[tuple[str, str]], skip_empty: bool) -> str:
    """ "key=value&key=value" in the given order, the text PayFast's signature is made from.
    Checkout forms leave empty fields out; notices keep them."""
    return "&".join(
        f"{name}={encode_param(value)}" for name, value in fields if value or not skip_empty
    )


def sign(param_string: str, passphrase: str) -> str:
    """PayFast's signature: the MD5 of the param string, with the passphrase added if set."""
    if passphrase:
        param_string += f"&passphrase={encode_param(passphrase)}"
    return hashlib.md5(param_string.encode()).hexdigest()  # noqa: S324 (PayFast's own scheme)


class PayFastPaymentProvider:
    """PayFast's hosted checkout and ITN webhook. https://developers.payfast.co.za/docs

    A notice counts only when its signature is right, it's for our merchant, and PayFast's own
    server says it's VALID. PayFast's docs also suggest checking the sender's IP address; that is
    left out, because behind Render's proxy the address can't be trusted, and asking PayFast
    back covers the same risk. The amount is compared by the caller (confirm_payment).
    """

    name = "payfast"

    def __init__(
        self,
        merchant_id: str,
        merchant_key: str,
        passphrase: str,
        is_sandbox: bool,
        client: httpx.Client | None = None,
    ):
        self.merchant_id = merchant_id
        self.merchant_key = merchant_key
        self.passphrase = passphrase
        self.host = PAYFAST_SANDBOX_HOST if is_sandbox else PAYFAST_LIVE_HOST
        self.client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def create_checkout(self, request: CheckoutRequest) -> Checkout:
        """PayFast's form, in the field order its signature expects, signed."""
        fields = [
            ("merchant_id", self.merchant_id),
            ("merchant_key", self.merchant_key),
            ("return_url", request.return_url),
            ("cancel_url", request.cancel_url),
            ("notify_url", request.notify_url),
            ("m_payment_id", request.payment_id),
            ("amount", format_rands(request.amount_rands)),
            ("item_name", request.item_name),
        ]
        signature = sign(build_param_string(fields, skip_empty=True), self.passphrase)
        return Checkout(
            url=f"{self.host}{PAYFAST_PROCESS_PATH}",
            method="POST",
            fields={name: value for name, value in fields if value} | {"signature": signature},
        )

    def read_notice(self, fields: Sequence[tuple[str, str]]) -> PaymentNotice:
        values = dict(fields)
        self.check_signature(fields, values.get("signature", ""))
        if values.get("merchant_id") != self.merchant_id:
            raise PaymentNoticeError("The notice is for another merchant")
        self.check_with_payfast(fields)
        try:
            amount_cents = round(float(values["amount_gross"]) * CENTS_PER_RAND)
            return PaymentNotice(
                payment_id=values["m_payment_id"],
                paid=values.get("payment_status") == PAYFAST_COMPLETE_STATUS,
                amount_cents=amount_cents,
                reference=values.get("pf_payment_id", ""),
            )
        except (KeyError, ValueError) as problem:
            raise PaymentNoticeError(f"The notice is missing {problem}") from problem

    def check_signature(self, fields: Sequence[tuple[str, str]], signature: str) -> None:
        """Signs every field before the signature, empty ones included, as PayFast does."""
        signed_fields = []
        for name, value in fields:
            if name == "signature":
                break
            signed_fields.append((name, value))
        expected = sign(build_param_string(signed_fields, skip_empty=False), self.passphrase)
        if not hmac.compare_digest(expected, signature):
            raise PaymentNoticeError("The notice's signature is wrong")

    def check_with_payfast(self, fields: Sequence[tuple[str, str]]) -> None:
        """Sends the notice back to PayFast, which answers VALID only for one it really sent."""
        param_string = build_param_string(
            [(name, value) for name, value in fields if name != "signature"], skip_empty=False
        )
        try:
            response = self.client.post(
                f"{self.host}{PAYFAST_VALIDATE_PATH}",
                content=param_string,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        except httpx.HTTPError as problem:
            raise PaymentNoticeError(f"PayFast couldn't be asked: {problem!r}") from problem
        if response.text.strip() != PAYFAST_VALID_ANSWER:
            raise PaymentNoticeError("PayFast says the notice isn't valid")


def get_payment_provider() -> PaymentProvider:
    """PayFast when PAYMENT_PROVIDER=payfast (its keys from the environment), else the mock.
    FastAPI dependency; tests replace it."""
    if os.environ.get("PAYMENT_PROVIDER", "mock") != "payfast":
        return MockPaymentProvider()
    return PayFastPaymentProvider(
        merchant_id=os.environ["PAYFAST_MERCHANT_ID"],
        merchant_key=os.environ["PAYFAST_MERCHANT_KEY"],
        passphrase=os.environ.get("PAYFAST_PASSPHRASE", ""),
        is_sandbox=os.environ.get("PAYFAST_SANDBOX", "true").lower() != "false",
    )
