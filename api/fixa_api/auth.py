"""Login for the seeded demo users: a fixed OTP, then a JWT that says who is calling.

Settings come from the environment: DEMO_OTP (default 123456) and JWT_SECRET.
Routes use `current_user` to know who is calling, or `require_role` to allow only one role.
"""

import datetime as dt
import os
import re
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from fixa_api.db import get_session
from fixa_api.models import Customer, Provider

TOKEN_LIFETIME = dt.timedelta(days=7)
TOKEN_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(auto_error=False)


def demo_otp() -> str:
    return os.environ.get("DEMO_OTP", "123456")


def jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", "change-me")


def normalise_phone(phone: str) -> str:
    """Keep the digits only and use the local 0 prefix, so "+27 82 000 0001" == "082 000 0001"."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("27") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def find_user_by_phone(session: Session, phone: str) -> Customer | Provider | None:
    """Return the customer or provider with this phone number, or None."""
    wanted = normalise_phone(phone)
    for table in (Customer, Provider):
        for user in session.exec(select(table)):
            if normalise_phone(user.phone) == wanted:
                return user
    return None


def find_user_by_id(session: Session, user_id: str) -> Customer | Provider | None:
    return session.get(Customer, user_id) or session.get(Provider, user_id)


def create_token(user: Customer | Provider) -> str:
    claims = {"sub": user.id, "exp": dt.datetime.now(dt.UTC) + TOKEN_LIFETIME}
    return jwt.encode(claims, jwt_secret(), algorithm=TOKEN_ALGORITHM)


def user_summary(user: Customer | Provider) -> dict[str, str]:
    """The User shape of the contract. It has no phone, address or location."""
    return {
        "id": user.id,
        "role": user.role,
        "display_name": user.display_name,
        "lang": user.lang,
        "suburb": user.suburb,
        "id_badge": user.id_badge,
    }


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> Customer | Provider:
    """The signed-in user, or a 401 when the token is missing, expired, bad or for a gone user."""
    unauthorised = HTTPException(status_code=401, detail="Sign in first")
    if credentials is None:
        raise unauthorised
    try:
        claims = jwt.decode(credentials.credentials, jwt_secret(), algorithms=[TOKEN_ALGORITHM])
    except jwt.InvalidTokenError:
        raise unauthorised from None
    user = find_user_by_id(session, str(claims.get("sub")))
    if user is None:
        raise unauthorised
    return user


def require_role(role: str):
    """A dependency that allows one role only (403 for the other)."""

    def check(user: Annotated[Customer | Provider, Depends(current_user)]) -> Customer | Provider:
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Only a {role} can do this")
        return user

    return check
