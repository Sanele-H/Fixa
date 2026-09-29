"""Chat on a job. The app polls GET every 3 seconds with ?after=<message_id>."""

from fastapi import APIRouter
from pydantic import BaseModel

from fixa_api.fixtures import load_fixture

router = APIRouter(prefix="/api", tags=["chat"])


class NewMessage(BaseModel):
    text: str


@router.get("/jobs/{job_id}/messages")
def read_messages(job_id: str, after: str | None = None):
    return load_fixture("messages.json")


@router.post("/jobs/{job_id}/messages", status_code=201)
def send_message(job_id: str, body: NewMessage):
    return load_fixture("message.json")
