"""Login and the signed-in user. Demo users log in with OTP 123456."""

import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session

from fixa_api.auth import (
    create_token,
    current_user,
    demo_otp,
    find_user_by_phone,
    user_summary,
)
from fixa_api.db import get_session
from fixa_api.models import Customer, Provider

router = APIRouter(prefix="/api", tags=["auth"])


class OtpRequest(BaseModel):
    phone: str


class VerifyRequest(BaseModel):
    phone: str
    otp: str


class UpdateMe(BaseModel):
    lang: Literal["en", "zu", "xh"]


@router.post("/auth/otp", status_code=204)
def send_otp(body: OtpRequest) -> Response:
    """Demo login has no real SMS: the code is always DEMO_OTP. Answers 204 for any number, so
    the endpoint can't be used to find out who has an account."""
    return Response(status_code=204)


@router.post("/auth/verify")
def verify_otp(body: VerifyRequest, session: Annotated[Session, Depends(get_session)]):
    user = find_user_by_phone(session, body.phone)
    # compare_digest and one shared error, so a wrong code and an unknown number look the same
    otp_ok = secrets.compare_digest(body.otp.encode(), demo_otp().encode())
    if user is None or not otp_ok:
        raise HTTPException(status_code=401, detail="Wrong phone number or code")
    return {"token": create_token(user), "user": user_summary(user)}


@router.get("/me")
def read_me(user: Annotated[Customer | Provider, Depends(current_user)]):
    return user_summary(user)


@router.patch("/me")
def update_me(
    body: UpdateMe,
    user: Annotated[Customer | Provider, Depends(current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    user.lang = body.lang
    session.add(user)
    session.commit()
    session.refresh(user)
    return user_summary(user)
