"""The work statement: confirmed jobs and agreed amounts, for credit or renting, in any trade.

It is labelled "Customer-confirmed, not a bank statement" at the top and in every page's
footer: customers confirmed the jobs and the amounts they agreed, but Fixa never sees
payments.
"""

from collections import defaultdict

from record.experience import CONFIRMATION_NAMES
from record.models import RecordEvidence, RecordJob
from record.pdf_layout import RecordPdf, format_date
from record.sections import RecordCover, write_verify_block

STATEMENT_LABEL = "Customer-confirmed, not a bank statement"
STATEMENT_EXPLANATION = (
    "Customers confirmed these jobs, and the amounts they agreed, in the Fixa app or by "
    "replying to an SMS or USSD message. Fixa doesn't see payments: this is not a bank "
    "statement, and the amounts are not proof of money received."
)
NOT_RECORDED = "not recorded"
MONTH_COLUMN_WIDTHS_MM = [40, 40, 94]
JOB_COLUMN_WIDTHS_MM = [24, 56, 38, 32, 24]


def write_statement_record(pdf: RecordPdf, evidence: RecordEvidence, cover: RecordCover) -> None:
    """Writes the work statement: summary, verify block, months, then every job."""
    jobs = sorted(evidence.jobs, key=lambda job: job.done_on)
    pdf.write_title("Work statement")
    pdf.write_text(STATEMENT_LABEL, bold=True)
    pdf.write_text(f"Provider: {evidence.display_name}", bold=True)
    pdf.write_text(f"Trades: {', '.join(format_trade_name(trade) for trade in evidence.trades)}")
    write_totals(pdf, jobs)
    pdf.write_note(STATEMENT_EXPLANATION)
    write_verify_block(pdf, cover)
    write_months(pdf, jobs)
    write_jobs(pdf, jobs)


def write_totals(pdf: RecordPdf, jobs: list[RecordJob]) -> None:
    """Writes the period covered, the number of jobs and the total of agreed amounts."""
    if not jobs:
        pdf.write_text("No confirmed jobs yet.")
        return
    amounts = [job.amount_rands for job in jobs if job.amount_rands is not None]
    pdf.write_text(
        f"Period: {format_date(jobs[0].done_on)} to {format_date(jobs[-1].done_on)}. "
        f"Confirmed jobs: {len(jobs)}. Agreed amounts: {format_rands(sum(amounts))} "
        f"across {len(amounts)} job{'s' if len(amounts) != 1 else ''} with an amount recorded."
    )


def write_months(pdf: RecordPdf, jobs: list[RecordJob]) -> None:
    """Writes one row per month: confirmed jobs and the total of agreed amounts."""
    pdf.write_heading("By month")
    jobs_by_month: dict[str, list[RecordJob]] = defaultdict(list)
    for job in jobs:
        jobs_by_month[job.done_on.strftime("%Y-%m")].append(job)
    rows = [
        [
            month_jobs[0].done_on.strftime("%B %Y"),
            str(len(month_jobs)),
            format_month_amounts(month_jobs),
        ]
        for _, month_jobs in sorted(jobs_by_month.items())
    ]
    pdf.write_table(["Month", "Confirmed jobs", "Agreed amounts"], rows, MONTH_COLUMN_WIDTHS_MM)


def write_jobs(pdf: RecordPdf, jobs: list[RecordJob]) -> None:
    """Writes every confirmed job with how it was confirmed and its agreed amount."""
    pdf.write_heading("Confirmed jobs")
    rows = [
        [
            format_date(job.done_on),
            job.trade_task,
            job.suburb,
            capitalise_first_letter(CONFIRMATION_NAMES[job.confirmed_via]),
            format_rands(job.amount_rands) if job.amount_rands is not None else NOT_RECORDED,
        ]
        for job in jobs
    ]
    headings = ["Date", "Trade task", "Suburb", "Confirmed", "Agreed"]
    pdf.write_table(headings, rows, JOB_COLUMN_WIDTHS_MM)


def format_month_amounts(month_jobs: list[RecordJob]) -> str:
    """Totals a month's agreed amounts, or "not recorded" if none of its jobs has one."""
    amounts = [job.amount_rands for job in month_jobs if job.amount_rands is not None]
    return format_rands(sum(amounts)) if amounts else NOT_RECORDED


def capitalise_first_letter(text: str) -> str:
    """Capitalises only the first letter, so "by customer SMS" keeps its SMS."""
    return text[:1].upper() + text[1:]


def format_rands(amount_rands: int) -> str:
    """Formats rands the South African way, with a space between thousands: R12 450."""
    return f"R{amount_rands:,}".replace(",", " ")


def format_trade_name(trade: str) -> str:
    """Turns a glossary trade id such as "appliance_repair" into "Appliance repair"."""
    return trade.replace("_", " ").capitalize()
