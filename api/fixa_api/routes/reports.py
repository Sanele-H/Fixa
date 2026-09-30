"""The report button: anyone can flag a job, a provider or a message the checks missed.

Reports go to the team (the report table) and change nothing on their own: a person decides.
Not in contracts/api.md yet.
"""

import datetime as dt
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from fixa_api.auth import current_user
from fixa_api.db import get_session
from fixa_api.job_views import can_see_job
from fixa_api.messages import can_read, is_chat_party
from fixa_api.models import Customer, Job, Message, Provider, Report

router = APIRouter(prefix="/api", tags=["reports"])

MAX_REPORTS_PER_DAY = 20
User = Annotated[Customer | Provider, Depends(current_user)]
DbSession = Annotated[Session, Depends(get_session)]


class NewReport(BaseModel):
    target_type: Literal["job", "provider", "message"]
    target_id: str = Field(min_length=1, max_length=64)
    reason: Literal["illegal_work", "scam", "abuse", "fake_profile", "other"]
    note: str | None = Field(default=None, max_length=500)


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Nothing to report there")


def check_can_report(session: Session, reporter: Customer | Provider, body: NewReport) -> None:
    """The reporter must be someone who can see what they report, and can't report themselves.
    Anything else gets the same 404 as something that doesn't exist."""
    if body.target_type == "provider":
        if session.get(Provider, body.target_id) is None:
            raise not_found()
        if body.target_id == reporter.id:
            raise HTTPException(status_code=422, detail="You can't report yourself")
    elif body.target_type == "job":
        job = session.get(Job, body.target_id)
        if job is None or not can_see_job(session, job, reporter):
            raise not_found()
        if job.customer_id == reporter.id:
            raise HTTPException(status_code=422, detail="You can't report your own job")
    else:
        message = session.get(Message, body.target_id)
        job = session.get(Job, message.job_id) if message else None
        if (
            job is None
            or not is_chat_party(session, job, reporter)
            or not can_read(message, job, reporter)
        ):
            raise not_found()
        if message.sender_id == reporter.id:
            raise HTTPException(status_code=422, detail="You can't report your own message")


@router.post("/reports", status_code=201)
def create_report(body: NewReport, reporter: User, session: DbSession):
    """Send a report to the team. One report per person, target and reason."""
    check_can_report(session, reporter, body)
    mine = list(session.exec(select(Report).where(Report.reporter_id == reporter.id)))
    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
    if len([report for report in mine if report.created_at >= since]) >= MAX_REPORTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many reports today. Try again tomorrow.")
    same = [
        report
        for report in mine
        if (report.target_type, report.target_id, report.reason)
        == (body.target_type, body.target_id, body.reason)
    ]
    if same:
        raise HTTPException(status_code=409, detail="You already reported this")
    report = Report(
        id=f"report_{uuid.uuid4().hex[:10]}",
        reporter_id=reporter.id,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        note=body.note,
        created_at=dt.datetime.now(dt.UTC),
    )
    session.add(report)
    session.commit()
    return {"id": report.id, "status": "received"}
