"""Sections both kinds of record share: the verify block and the before/after photos."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from record.models import RecordJob
from record.pdf_layout import (
    FONT_FAMILY,
    MARGIN_MM,
    NOTE_SIZE_PT,
    SECONDARY_INK,
    RecordPdf,
    format_date,
)

QR_SIZE_MM = 30
VERIFY_TEXT_WIDTH_MM = 130
PHOTO_WIDTH_MM = 82
PHOTO_HEIGHT_MM = 60
PHOTO_GAP_MM = 6
PHOTO_ROW_MM = PHOTO_HEIGHT_MM + 14  # a caption line plus the photos


@dataclass(frozen=True)
class RecordCover:
    """What identifies one issued record: its code, fingerprint, date and verify link."""

    verify_code: str
    sha256: str
    issued_on: date
    verify_url: str | None  # absolute link for the QR code; None when P2 gave no base URL


def write_verify_block(pdf: RecordPdf, cover: RecordCover) -> None:
    """Writes how to check the record is genuine, with a QR code on the right if there's a link."""
    top_mm = pdf.get_y()
    if cover.verify_url:
        pdf.draw_qr_code(cover.verify_url, pdf.w - MARGIN_MM - QR_SIZE_MM, top_mm, QR_SIZE_MM)
        where = f"scan the QR code or open {cover.verify_url}"
    else:
        where = f"open /verify/{cover.verify_code} on the Fixa website"
    pdf.set_xy(MARGIN_MM, top_mm)
    lines = [
        f"Check this record is genuine: {where}.",
        f"Verify code: {cover.verify_code}   ·   Issued {format_date(cover.issued_on)}",
        f"Fingerprint (SHA-256): {cover.sha256}",
    ]
    for line in lines:
        pdf.write_block(
            line,
            NOTE_SIZE_PT + 0.5,
            SECONDARY_INK,
            line_height_mm=4.6,
            width_mm=VERIFY_TEXT_WIDTH_MM,
        )
    pdf.set_y(max(pdf.get_y(), top_mm + (QR_SIZE_MM if cover.verify_url else 0)) + 2)


def write_photo_pages(pdf: RecordPdf, jobs: list[RecordJob], photos: Mapping[str, bytes]) -> int:
    """Writes the before/after photos of each job, side by side. Returns how many were shown.

    Photos whose bytes weren't passed in, or aren't a readable image, are left out.
    """
    shown_count = 0
    for job in jobs:
        available = [photo for photo in job.photos if photo.photo_id in photos]
        if not available:
            continue
        if pdf.get_y() + PHOTO_ROW_MM > pdf.h - MARGIN_MM - 10:
            pdf.add_page()
        pdf.write_note(f"{format_date(job.done_on)} · {job.trade_task} · {job.suburb}")
        shown_count += draw_photo_row(
            pdf, sorted(available, key=lambda p: p.kind != "before"), photos
        )
    return shown_count


def draw_photo_row(pdf: RecordPdf, job_photos: list, photos: Mapping[str, bytes]) -> int:
    """Draws up to two photos of one job side by side, labelled before and after."""
    top_mm = pdf.get_y()
    shown_count = 0
    for position, photo in enumerate(job_photos[:2]):
        x_mm = MARGIN_MM + position * (PHOTO_WIDTH_MM + PHOTO_GAP_MM)
        if pdf.draw_photo(photos[photo.photo_id], x_mm, top_mm, PHOTO_WIDTH_MM, PHOTO_HEIGHT_MM):
            pdf.set_xy(x_mm, top_mm + PHOTO_HEIGHT_MM + 0.5)
            pdf.set_font(FONT_FAMILY, size=NOTE_SIZE_PT)
            pdf.cell(PHOTO_WIDTH_MM, 4, photo.kind.capitalize())
            shown_count += 1
    pdf.set_xy(MARGIN_MM, top_mm + PHOTO_HEIGHT_MM + 6)
    return shown_count
