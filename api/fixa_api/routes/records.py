"""Work record export, and the plain-HTML link pages (/record/... and /verify/...)."""

import datetime as dt
import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from fixa_api.auth import require_role
from fixa_api.db import get_session
from fixa_api.models import ExportedRecord, Provider
from fixa_api.record_evidence import build_evidence
from record import (
    ArplTradeError,
    RecordEvidence,
    StoredRecord,
    build_record,
    render_verify_page,
    render_work_record_page,
    verify_record,
)

router = APIRouter(tags=["records"])

MAX_EXPORTS_PER_DAY = 10  # each export builds a PDF, so keep one account from hammering it
PDF_SUFFIX = ".pdf"
NOT_FOUND_PAGE = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<title>Not found</title></head><body><h1>Not found</h1>"
    "<p>There is no work record at this address.</p></body></html>"
)
ProviderUser = Annotated[Provider, Depends(require_role("provider"))]
DbSession = Annotated[Session, Depends(get_session)]


class ExportRequest(BaseModel):
    mode: Literal["arpl", "statement"]


def public_base_url(request: Request) -> str:
    """The site's address for the QR code. Set PUBLIC_BASE_URL on the live server, where the
    address the API sees may be an internal one."""
    return os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)


def html_page(html: str, status_code: int = 200) -> HTMLResponse:
    """A link page. noindex, because these pages are for people who were sent the link."""
    return HTMLResponse(html, status_code=status_code, headers={"X-Robots-Tag": "noindex"})


def exports_today(session: Session, provider: Provider, now: dt.datetime) -> int:
    since = now - dt.timedelta(days=1)
    query = select(ExportedRecord).where(
        ExportedRecord.provider_id == provider.id, ExportedRecord.created_at >= since
    )
    return len(list(session.exec(query)))


@router.post("/api/record/export")
def export_record(
    body: ExportRequest, provider: ProviderUser, session: DbSession, request: Request
):
    """Build the provider's work record PDF and keep what /verify/{code} needs to check it."""
    now = dt.datetime.now(dt.UTC)
    if exports_today(session, provider, now) >= MAX_EXPORTS_PER_DAY:
        raise HTTPException(status_code=429, detail="Too many exports today. Try again tomorrow.")
    evidence = build_evidence(session, provider)
    if not evidence.jobs:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_jobs", "message": "There are no confirmed jobs to export yet"},
        )
    try:
        document = build_record(evidence, body.mode, verify_base_url=public_base_url(request))
    except ArplTradeError:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_arpl_trade",
                "message": "ARPL records are only for trades that have an ARPL toolkit",
            },
        ) from None
    session.add(
        ExportedRecord(
            verify_code=document.verify_code,
            provider_id=provider.id,
            mode=body.mode,
            sha256=document.sha256,
            evidence=evidence.model_dump(mode="json"),
            issued_on=now.date(),
            created_at=now,
            pdf=document.pdf_bytes,
        )
    )
    session.commit()
    return {
        "verify_code": document.verify_code,
        "download_url": f"/api/record/exports/{document.verify_code}{PDF_SUFFIX}",
        "sha256": document.sha256,
    }


@router.get("/api/record/exports/{filename}")
def download_export(filename: str, provider: ProviderUser, session: DbSession):
    """The PDF of an export, for the provider who made it."""
    code = filename.removesuffix(PDF_SUFFIX).upper()
    row = session.get(ExportedRecord, code)
    if not filename.endswith(PDF_SUFFIX) or row is None or row.provider_id != provider.id:
        raise HTTPException(status_code=404, detail="Export not found")
    return Response(
        row.pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fixa-record-{code}.pdf"'},
    )


@router.get("/record/{provider_id}", response_class=HTMLResponse)
def read_work_record(provider_id: str, session: DbSession):
    """A provider's work record as a plain web page, for anyone they send the link to.

    It only exists for a provider who has exported a record, which is their sign that they want
    it shared, so the page can't be used to browse everyone's history by trying ids. It shows
    suburbs, dates and tasks: never a customer's name, number or address.
    """
    provider = session.get(Provider, provider_id)
    exported = session.exec(
        select(ExportedRecord).where(ExportedRecord.provider_id == provider_id)
    ).first()
    if provider is None or exported is None:
        return html_page(NOT_FOUND_PAGE, status_code=404)
    return html_page(render_work_record_page(build_evidence(session, provider)))


@router.get("/verify/{code}", response_class=HTMLResponse)
def verify_record_page(code: str, session: DbSession):
    """Tells anyone with a record's code or QR whether it is genuine and unchanged."""
    row = session.get(ExportedRecord, code.strip().upper())
    stored = None
    if row is not None:
        stored = StoredRecord(
            verify_code=row.verify_code,
            sha256=row.sha256,
            mode=row.mode,
            evidence=RecordEvidence.model_validate(row.evidence),
            issued_on=row.issued_on,
        )
    result = verify_record(code, stored)
    return html_page(render_verify_page(code, result), status_code=200 if stored else 404)
