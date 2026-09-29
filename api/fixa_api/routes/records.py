"""Work record export and the plain-HTML link pages (still placeholders until step 12)."""

from html import escape
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from fixa_api.fixtures import load_fixture

router = APIRouter(tags=["records"])


class ExportRequest(BaseModel):
    mode: Literal["arpl", "statement"]


def plain_page(title: str, text: str) -> HTMLResponse:
    """A placeholder link page: plain HTML with no JavaScript. P4's templates replace it."""
    title, text = escape(title), escape(text)
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{title}</title></head><body><h1>{title}</h1><p>{text}</p></body></html>"
    )


@router.post("/api/record/export")
def export_record(body: ExportRequest):
    return load_fixture("record_export.json")


@router.get("/record/{provider_id}", response_class=HTMLResponse)
def read_work_record(provider_id: str):
    return plain_page("Work record", f"Work record for {provider_id}.")


@router.get("/verify/{code}", response_class=HTMLResponse)
def verify_record_page(code: str):
    return plain_page("Verify a record", f"Checking record {code}.")
