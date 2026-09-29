"""ID checks: the offline number check and the Home Affairs check."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from fixa_api.fixtures import load_fixture

router = APIRouter(prefix="/api/identity", tags=["identity"])


class IdNumber(BaseModel):
    id_number: str


class IdVerification(BaseModel):
    id_number: str
    names: str
    consent: Literal[True]


@router.post("/check-number")
def check_id_number(body: IdNumber):
    return load_fixture("id_number_check.json")


@router.post("/verify")
def verify_identity(body: IdVerification):
    return load_fixture("id_result.json")
