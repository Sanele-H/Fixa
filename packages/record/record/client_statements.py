"""Client statements: one page per reference, to sign before a Commissioner of Oaths.

Each is pre-filled with the job (task, date, suburb) and left blank for the customer's own
name, ID number, contact number and signature, so Fixa never prints them. Only customers
who agreed to be references get one. With many references, up to MAX_CLIENT_STATEMENTS are
chosen, spread across the record's dates so they back up the whole span of experience.
"""

from record.models import RecordJob
from record.pdf_layout import (
    BODY_SIZE_PT,
    FONT_FAMILY,
    MARGIN_MM,
    SECONDARY_INK,
    RecordPdf,
    format_date,
)

MAX_CLIENT_STATEMENTS = 6
BLANK_LABEL_WIDTH_MM = 55
BLANK_ROW_MM = 10
BLANK_LINE_RAISE_MM = 2.5  # the writing line sits just under the label's baseline
STAMP_BOX_MM = (55, 40)  # beside the commissioner's four fields
STAMP_GAP_MM = 6
CUSTOMER_FIELDS = [
    "Full names and surname",
    "ID or passport number",
    "Contact number",
    "Signature",
    "Date (DD/MM/YYYY)",
]
COMMISSIONER_FIELDS = [
    "Full names",
    "Designation and area",
    "Signature",
    "Date and place",
]
COMMISSIONER_CERTIFICATE = (
    "I certify that the customer has acknowledged that they know and understand the contents "
    "of this statement, which was signed and sworn to or affirmed before me. Stamp in the box."
)


def write_client_statements(
    pdf: RecordPdf, display_name: str, trade_title: str, jobs: list[RecordJob], verify_code: str
) -> None:
    """Writes one statement page per chosen reference job."""
    for job in choose_statement_jobs(jobs):
        write_client_statement(pdf, display_name, trade_title, job, verify_code)


def choose_statement_jobs(jobs: list[RecordJob]) -> list[RecordJob]:
    """Picks up to MAX_CLIENT_STATEMENTS reference jobs, evenly spread from oldest to newest."""
    reference_jobs = sorted((job for job in jobs if job.reference_agreed), key=lambda j: j.done_on)
    if len(reference_jobs) <= MAX_CLIENT_STATEMENTS:
        return reference_jobs
    last_index = len(reference_jobs) - 1
    step = last_index / (MAX_CLIENT_STATEMENTS - 1)
    return [reference_jobs[round(position * step)] for position in range(MAX_CLIENT_STATEMENTS)]


def write_client_statement(
    pdf: RecordPdf, display_name: str, trade_title: str, job: RecordJob, verify_code: str
) -> None:
    """Writes one client statement page, pre-filled with the job and blank for the customer."""
    pdf.add_page()
    pdf.write_title("Client statement")
    pdf.write_note(
        f"For an ARPL trade test application by {display_name} ({trade_title}). To be filled in "
        "by the customer and signed in front of a Commissioner of Oaths. Certified documents "
        "must not be older than three months."
    )
    pdf.write_heading("The work")
    pdf.write_text(f"Trade task: {job.trade_task}")
    pdf.write_text(f"Date: {format_date(job.done_on)}")
    pdf.write_text(f"Suburb: {job.suburb}")
    pdf.write_note(f"Recorded on Fixa, work record verify code {verify_code}.")
    pdf.write_heading("The customer")
    pdf.write_text(f"I confirm that {display_name} did the work described above for me at my home.")
    pdf.write_text("Comments about the work (optional):")
    write_blank_lines(pdf, ["", ""])
    write_blank_lines(pdf, CUSTOMER_FIELDS)
    pdf.write_heading("Commissioner of Oaths")
    pdf.write_note(COMMISSIONER_CERTIFICATE)
    fields_top_mm = pdf.get_y()
    stamp_x_mm = pdf.w - MARGIN_MM - STAMP_BOX_MM[0]
    write_blank_lines(pdf, COMMISSIONER_FIELDS, line_end_mm=stamp_x_mm - STAMP_GAP_MM)
    pdf.set_draw_color(*SECONDARY_INK)
    pdf.rect(stamp_x_mm, fields_top_mm, *STAMP_BOX_MM)  # room for the stamp


def write_blank_lines(pdf: RecordPdf, labels: list[str], line_end_mm: float | None = None) -> None:
    """Writes a label with a line beside it for each field, to be filled in by hand.

    An empty label gives a full-width line, for free text. Lines end at line_end_mm, or
    at the right margin.
    """
    line_end_mm = line_end_mm or pdf.w - MARGIN_MM
    pdf.set_font(FONT_FAMILY, size=BODY_SIZE_PT)
    pdf.set_text_color(*SECONDARY_INK)
    pdf.set_draw_color(*SECONDARY_INK)
    for label in labels:
        row_top_mm = pdf.get_y()
        pdf.text_log.append(label)
        pdf.cell(BLANK_LABEL_WIDTH_MM if label else 0, BLANK_ROW_MM, label)
        line_start_mm = MARGIN_MM + (BLANK_LABEL_WIDTH_MM if label else 0)
        line_y_mm = row_top_mm + BLANK_ROW_MM - BLANK_LINE_RAISE_MM
        pdf.line(line_start_mm, line_y_mm, line_end_mm, line_y_mm)
        pdf.set_xy(MARGIN_MM, row_top_mm + BLANK_ROW_MM)
    pdf.ln(2)
