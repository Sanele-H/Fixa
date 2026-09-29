"""ID checks for providers.

Tier 1, `id_number`: the number is a well-formed South African ID (checked here, offline).
Tier 2, `home_affairs`: a verifier confirms the number and the name against Home Affairs records.

Verifiers sit behind one interface, IdentityVerifier: SmileIdVerifier (Smile ID) and
MockVerifier (no network, for building and for the demo if the sandbox is slow). Pick one with
IDENTITY_VERIFIER=mock|smile. Only the result is ever stored, never the ID number or the names
(POPIA treats them as special personal information).
"""

import datetime as dt
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

ID_NUMBER_LENGTH = 13
BIRTH_DATE_LENGTH = 6
TIER_NONE = "none"
TIER_ID_NUMBER = "id_number"
TIER_HOME_AFFAIRS = "home_affairs"
TIER_ORDER = [TIER_NONE, TIER_ID_NUMBER, TIER_HOME_AFFAIRS]
SMILE_ENHANCED_KYC_JOB_TYPE = 5
SMILE_SANDBOX_SERVER = 0
SMILE_PRODUCTION_SERVER = 1
SMILE_NAME_MATCHES = {"Exact Match", "Partial Match"}


# --- the offline check ----------------------------------------------------------------------


def luhn_check_digit(first_twelve_digits: str) -> str:
    """The 13th digit that makes a South African ID number pass the Luhn checksum."""
    total = 0
    for position, digit in enumerate(reversed(first_twelve_digits)):
        value = int(digit)
        if position % 2 == 0:  # every second digit from the right, counting the missing check digit
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return str((10 - total % 10) % 10)


def passes_luhn(id_number: str) -> bool:
    return luhn_check_digit(id_number[:-1]) == id_number[-1]


def read_birth_date(id_number: str, today: dt.date) -> dt.date | None:
    """The date of birth in the first six digits (YYMMDD), or None if it isn't a real date.
    Two-digit years are ambiguous, so a year later than this year's is read as the 1900s."""
    year, month, day = (int(id_number[i : i + 2]) for i in (0, 2, 4))
    century = 2000 if year <= today.year % 100 else 1900
    try:
        birth_date = dt.date(century + year, month, day)
    except ValueError:
        return None
    return birth_date if birth_date <= today else None


def check_id_number(id_number: str, today: dt.date | None = None) -> dict[str, Any]:
    """The offline check, in the shape of id_number_check.json.

    reason is None when valid, else "digits" (not only digits), "length" (not 13 digits),
    "date" (not a real birth date) or "checksum" (the check digit is wrong: usually a typo).
    """
    today = today or dt.datetime.now(dt.UTC).date()
    cleaned = re.sub(r"[\s-]", "", id_number)
    reason = None
    birth_date = None
    if not cleaned.isdigit():
        reason = "digits"
    elif len(cleaned) != ID_NUMBER_LENGTH:
        reason = "length"
    else:
        birth_date = read_birth_date(cleaned, today)
        if birth_date is None:
            reason = "date"
        elif not passes_luhn(cleaned):
            reason = "checksum"
    valid = reason is None
    return {
        "valid": valid,
        "reason": reason,
        "date_of_birth": birth_date.isoformat() if valid and birth_date else None,
    }


def clean_id_number(id_number: str) -> str:
    return re.sub(r"[\s-]", "", id_number)


# --- verifiers ------------------------------------------------------------------------------


@dataclass
class IdResult:
    """What a verifier says. `tier` is set by the route, from this and the offline check."""

    verified: bool  # Home Affairs knows this ID number
    name_match: bool  # and the name given matches it
    provider: str
    reference: str


class VerifierUnavailableError(Exception):
    """The verifier could not be reached or refused the request. Nothing is recorded."""


class IdentityVerifier(Protocol):
    def verify(self, id_number: str, names: str, consent: bool) -> IdResult: ...


def name_words(names: str) -> set[str]:
    return {word for word in re.split(r"[\s,.-]+", names.lower()) if word}


def make_mock_register() -> dict[str, str]:
    """Demo people the mock verifier knows: valid ID numbers, with the name on record."""

    def make_id(birth_date: str, sequence: str) -> str:
        first_twelve = f"{birth_date}{sequence}08"  # 0 = citizen, 8 = the usual next digit
        return first_twelve + luhn_check_digit(first_twelve)

    return {
        make_id("800101", "5009"): "Thabo Nkosi",
        make_id("850615", "0123"): "Sipho Dlamini",
        make_id("900220", "4321"): "Nosipho Khumalo",
    }


MOCK_REGISTER = make_mock_register()


class MockVerifier:
    """Answers from MOCK_REGISTER, like the sandbox would: an ID on the register is verified,
    and the name matches when every word given is in the name on record. Any other ID that
    passes the offline check is not found."""

    provider = "mock_sandbox"

    def verify(self, id_number: str, names: str, consent: bool) -> IdResult:
        recorded_name = MOCK_REGISTER.get(clean_id_number(id_number))
        verified = recorded_name is not None
        name_match = verified and name_words(names) <= name_words(recorded_name)
        return IdResult(
            verified=verified,
            name_match=name_match and bool(name_words(names)),
            provider=self.provider,
            reference=f"mock-{uuid.uuid4().hex[:10]}",
        )


class SmileIdVerifier:
    """Smile ID's Enhanced KYC (job type 5) for a South African national ID number.

    Needs SMILE_ID_PARTNER_ID and SMILE_ID_API_KEY. SMILE_ID_ENVIRONMENT is "sandbox" (default)
    or "production". Built from the smile-id-core package's own interface; it has not been run
    against the live sandbox yet, so test it once with real sandbox keys before the demo.
    """

    def __init__(self, api_factory=None):
        partner_id = os.environ.get("SMILE_ID_PARTNER_ID")
        api_key = os.environ.get("SMILE_ID_API_KEY")
        if not partner_id or not api_key:
            raise VerifierUnavailableError("Smile ID keys are not set")
        production = os.environ.get("SMILE_ID_ENVIRONMENT", "sandbox").lower() == "production"
        server = SMILE_PRODUCTION_SERVER if production else SMILE_SANDBOX_SERVER
        self.provider = "smile_id" if production else "smile_id_sandbox"
        if api_factory is None:
            from smile_id_core import IdApi

            api_factory = IdApi
        self.api = api_factory(partner_id, api_key, server)

    def verify(self, id_number: str, names: str, consent: bool) -> IdResult:
        first_name, _, last_name = names.strip().partition(" ")
        job_id = f"idcheck-{uuid.uuid4().hex}"
        partner_params = {
            "user_id": f"user-{uuid.uuid4().hex}",  # not our user id: nothing to link back
            "job_id": job_id,
            "job_type": SMILE_ENHANCED_KYC_JOB_TYPE,
        }
        id_params = {
            "country": "ZA",
            "id_type": "NATIONAL_ID",
            "id_number": clean_id_number(id_number),
            "first_name": first_name,
            "last_name": last_name,
        }
        try:
            response = self.api.submit_job(partner_params, id_params)
        except Exception as problem:  # network, bad keys, a rejected request
            raise VerifierUnavailableError("Smile ID could not check this ID") from problem
        actions = response.get("Actions") or {}
        return IdResult(
            verified=actions.get("Verify_ID_Number") == "Verified",
            name_match=actions.get("Names") in SMILE_NAME_MATCHES,
            provider=self.provider,
            reference=str(response.get("SmileJobID") or job_id),
        )


def get_verifier() -> IdentityVerifier:
    """The verifier named by IDENTITY_VERIFIER (default mock). FastAPI dependency; tests
    replace it."""
    name = os.environ.get("IDENTITY_VERIFIER", "mock").lower()
    if name == "mock":
        return MockVerifier()
    if name == "smile":
        return SmileIdVerifier()
    raise VerifierUnavailableError(f"Unknown IDENTITY_VERIFIER {name!r}")


def better_tier(current: str, new: str) -> str:
    """The higher of two tiers, so a later check never lowers a badge."""
    return max(current, new, key=TIER_ORDER.index)
