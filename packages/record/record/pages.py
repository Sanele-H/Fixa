"""The plain-HTML link pages P2 serves: the work record (/record/{provider_id}) and verify.

No JavaScript and inline CSS only, so they open in any browser, including Opera Mini, for
a few KB of data. Templates are in templates/. Everything shown is escaped, so a
customer's vouch can't inject HTML. The public work record shows no agreed amounts:
those appear only in the work statement PDF the provider chooses to share.

P2 usage:
    return HTMLResponse(render_work_record_page(evidence))
    return HTMLResponse(render_verify_page(code, verify_record(code, stored)))
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from record.experience import (
    CONFIRMATION_NAMES,
    format_duration,
    group_jobs_by_task,
    list_trade_jobs,
    summarise_experience,
)
from record.models import RecordEvidence, VerifyResult
from record.pdf_layout import format_date, hide_phone_numbers
from record.statement_record import format_trade_name

TEMPLATES_PATH = Path(__file__).resolve().parent / "templates"
RECENT_JOB_COUNT = 10
MODE_NAMES = {"arpl": "Work record for an ARPL application", "statement": "Work statement"}

# autoescape=True: every value is HTML-escaped, including customers' own words.
TEMPLATES = Environment(loader=FileSystemLoader(TEMPLATES_PATH), autoescape=True)


def render_work_record_page(evidence: RecordEvidence) -> str:
    """Renders a provider's public work record page as HTML."""
    return TEMPLATES.get_template("work_record.html").render(build_work_record_context(evidence))


def render_verify_page(verify_code: str, result: VerifyResult) -> str:
    """Renders the verify page for a code, from verify_record's result, as HTML."""
    return TEMPLATES.get_template("verify.html").render(build_verify_context(verify_code, result))


def build_work_record_context(evidence: RecordEvidence) -> dict:
    """Builds what the work record page shows, with dates already formatted.

    P2 can use this with its own template instead of work_record.html.
    """
    summary = summarise_experience(evidence.jobs)
    newest_first = sorted(evidence.jobs, key=lambda job: job.done_on, reverse=True)
    return {
        "display_name": evidence.display_name,
        "trades": [format_trade_name(trade) for trade in evidence.trades],
        "job_count": len(evidence.jobs),
        "experience_text": describe_experience(summary),
        "trade_sections": build_trade_sections(evidence),
        "vouches": [
            {
                "text": hide_phone_numbers(vouch.text),
                "suburb": vouch.suburb,
                "given_on": format_date(vouch.given_on),
            }
            for vouch in evidence.vouches
        ],
        "recent_jobs": [
            {
                "done_on": format_date(job.done_on),
                "trade_task": job.trade_task,
                "suburb": job.suburb,
                "confirmed_via": CONFIRMATION_NAMES[job.confirmed_via],
            }
            for job in newest_first[:RECENT_JOB_COUNT]
        ],
    }


def describe_experience(summary) -> str:
    """Describes the span of confirmed work, or "" when there are no jobs yet."""
    if summary.first_job_on is None:
        return ""
    return (
        f"confirmed work from {format_date(summary.first_job_on)} to "
        f"{format_date(summary.last_job_on)} ({format_duration(summary.span_months)})"
    )


def build_trade_sections(evidence: RecordEvidence) -> list[dict]:
    """Builds one table per trade with jobs: each trade task with its count and dates."""
    sections = []
    for trade in evidence.trades:
        task_rows = group_jobs_by_task(list_trade_jobs(evidence, trade))
        if task_rows:
            sections.append(
                {
                    "title": format_trade_name(trade),
                    "task_rows": [
                        {
                            "trade_task": row.trade_task,
                            "job_count": row.job_count,
                            "first_done_on": format_date(row.first_done_on),
                            "last_done_on": format_date(row.last_done_on),
                        }
                        for row in task_rows
                    ],
                }
            )
    return sections


def build_verify_context(verify_code: str, result: VerifyResult) -> dict:
    """Builds what the verify page shows, with dates already formatted."""
    return {
        "verify_code": verify_code.strip().upper(),
        "status": result.status,
        "display_name": result.display_name,
        "mode": result.mode,
        "mode_name": MODE_NAMES.get(result.mode, ""),
        "n_jobs": result.n_jobs,
        "first_job_on": format_date(result.first_job_on) if result.first_job_on else None,
        "last_job_on": format_date(result.last_job_on) if result.last_job_on else None,
        "issued_on": format_date(result.issued_on) if result.issued_on else None,
        "sha256": result.sha256,
    }
