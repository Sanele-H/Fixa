"""The ARPL work record: evidence for the merSETA ARPL Trade Test Application Form (LPM-FM-009).

It follows the form's own sections, so a provider can copy from it or attach it:
1. Summary, and how to check the record is genuine.
2. Experience against the form's qualifying criteria (18 months, 3 years or 4 years).
3. "Details of Experience" (form page 3): workplace, from, to, and practical tasks.
4. A dated timeline of confirmed work.
5. Testimonials: customers' own words, and how many agreed to be references.
6. What the application still needs, from the form's checklist (pages 5 and 6).
7. Appendix on the scope of workplace exposure: every job, then before/after photos.
8. Client statements for references to sign in front of a Commissioner of Oaths.

It supports an application and never claims anyone qualifies: merSETA decides what counts
as relevant experience, and the trade test is still required.
"""

from collections.abc import Mapping

from record.client_statements import write_client_statements
from record.experience import (
    ARPL_TRADE_TITLES,
    TaskExperience,
    choose_arpl_trade,
    count_jobs_by_year,
    describe_confirmations,
    format_duration,
    group_jobs_by_task,
    list_trade_jobs,
    summarise_experience,
)
from record.models import RecordEvidence, RecordJob
from record.pdf_layout import RecordPdf, format_date, hide_phone_numbers
from record.sections import PHOTO_ROW_MM, RecordCover, write_photo_pages, write_verify_block

FORM_NAME = "merSETA ARPL Trade Test Application Form (LPM-FM-009)"
DISCLAIMER = (
    "This record supports an ARPL application. It is not a qualification, a service letter "
    "or a certified document. merSETA decides what counts as relevant work experience, the "
    "application is reviewed, and the trade test is still required."
)
BAR_FULL_MONTHS = 60  # the bar runs to 5 years, so the 3 and 4 year marks have room
EXPERIENCE_MARKERS = [
    (18, "18 months (D, E)"),
    (36, "3 years (A, B, C, G)"),
    (48, "4 years (F)"),
]
STILL_NEEDED = [
    "The application form itself, fully completed, signed and dated.",
    "A certified copy of your ID, passport, or asylum or refugee papers.",
    "A certified copy of your educational qualification (the category you apply under "
    "depends on it).",
    "A service letter, or testimonials from people who can confirm your work. The client "
    "statements at the end of this record are for that.",
    "For trades with an ARPL toolkit (category G): the toolkit assessment, with its Portfolio "
    "of Evidence signed by the assessor.",
    "The form's medical information page.",
    "Certified documents must not be older than three months, and everything must be sent "
    "as PDF, not photos or scanner-app images.",
]
PHOTO_HEADING_ROOM_MM = 30  # the heading, a caption and the first row of photos
DETAILS_COLUMN_WIDTHS_MM = [44, 22, 22, 86]
APPENDIX_COLUMN_WIDTHS_MM = [22, 58, 36, 38, 20]
TIMELINE_COLUMN_WIDTHS_MM = [30, 40, 104]


def write_arpl_record(
    pdf: RecordPdf, evidence: RecordEvidence, cover: RecordCover, photos: Mapping[str, bytes]
) -> None:
    """Writes every section of the ARPL record for the provider's chosen ARPL trade."""
    trade = choose_arpl_trade(evidence)
    trade_title = ARPL_TRADE_TITLES[trade]
    jobs = list_trade_jobs(evidence, trade)
    write_summary(pdf, evidence, trade_title, jobs, cover)
    write_experience(pdf, jobs)
    write_details_of_experience(pdf, group_jobs_by_task(jobs))
    write_timeline(pdf, jobs)
    write_testimonials(pdf, evidence, jobs)
    write_still_needed(pdf)
    write_appendix(pdf, jobs, photos)
    write_client_statements(pdf, evidence.display_name, trade_title, jobs, cover.verify_code)


def write_summary(
    pdf: RecordPdf,
    evidence: RecordEvidence,
    trade_title: str,
    jobs: list[RecordJob],
    cover: RecordCover,
) -> None:
    """Writes the title, who the record is for, the disclaimer and the verify block."""
    pdf.write_title("Work record for an ARPL trade test application")
    pdf.write_note(f"Supporting evidence for the {FORM_NAME}.")
    pdf.write_text(f"Provider: {evidence.display_name}", bold=True)
    pdf.write_text(f"Trade test applying for (trade title): {trade_title}")
    pdf.write_text(f"Confirmed jobs in this trade: {len(jobs)}")
    pdf.write_note(DISCLAIMER)
    write_verify_block(pdf, cover)


def write_experience(pdf: RecordPdf, jobs: list[RecordJob]) -> None:
    """Writes the span of confirmed work against the form's experience requirements."""
    pdf.write_heading("Work experience")
    summary = summarise_experience(jobs)
    if summary.first_job_on is None:
        pdf.write_text("No confirmed jobs in this trade yet.")
        return
    pdf.write_text(
        f"Confirmed work from {format_date(summary.first_job_on)} to "
        f"{format_date(summary.last_job_on)}: {format_duration(summary.span_months)}. "
        f"{summary.months_with_work} of those {summary.calendar_months} calendar months "
        "had confirmed work."
    )
    pdf.draw_progress_bar(
        summary.span_months / BAR_FULL_MONTHS,
        [(months / BAR_FULL_MONTHS, label) for months, label in EXPERIENCE_MARKERS],
    )
    pdf.write_note(
        "The form's qualifying criteria ask for relevant work experience within South Africa: "
        "18 months (categories D and E, with an NCV Level 4 or N6), 3 years (A, B and C with "
        "the right certificate, or G with an ARPL toolkit assessment) or 4 years (F, with "
        "Grade 9). merSETA decides which experience is relevant to the trade."
    )


def write_details_of_experience(pdf: RecordPdf, task_rows: list[TaskExperience]) -> None:
    """Writes the form's "Details of Experience" table, one row per trade task."""
    pdf.write_heading("Details of experience (form page 3)")
    pdf.write_note(
        "Workplaces are customers' homes. Only suburbs are shown: Fixa never prints customers' "
        "names, phone numbers or addresses."
    )
    rows = [
        [
            f"Self-employed: customers' homes in {', '.join(row.suburbs)}",
            format_date(row.first_done_on),
            format_date(row.last_done_on),
            f"{row.trade_task}: {row.job_count} job{'s' if row.job_count != 1 else ''} "
            f"({describe_confirmations(row.confirmation_counts)})",
        ]
        for row in task_rows
    ]
    headings = ["Name and address of workplace", "From", "To", "Detail of practical tasks"]
    pdf.write_table(headings, rows, DETAILS_COLUMN_WIDTHS_MM)


def write_timeline(pdf: RecordPdf, jobs: list[RecordJob]) -> None:
    """Writes confirmed jobs per year, with the trade tasks done that year."""
    pdf.write_heading("Experience timeline")
    rows = []
    for year, job_count in count_jobs_by_year(jobs).items():
        year_tasks = sorted({job.trade_task for job in jobs if job.done_on.year == year})
        rows.append([str(year), f"{job_count} confirmed", ", ".join(year_tasks)])
    pdf.write_table(["Year", "Jobs", "Trade tasks"], rows, TIMELINE_COLUMN_WIDTHS_MM)


def write_testimonials(pdf: RecordPdf, evidence: RecordEvidence, jobs: list[RecordJob]) -> None:
    """Writes customers' vouches (suburb and date only) and how many agreed to be references."""
    pdf.write_heading("Testimonials")
    for vouch in evidence.vouches:
        pdf.write_text(f"“{hide_phone_numbers(vouch.text)}”")
        pdf.write_note(f"Customer in {vouch.suburb}, {format_date(vouch.given_on)}")
    reference_count = sum(job.reference_agreed for job in jobs)
    if not evidence.vouches:
        pdf.write_note("No written vouches yet.")
    pdf.write_text(
        f"{reference_count} customer{'s' if reference_count != 1 else ''} agreed to be "
        "contacted as a reference. Fixa keeps their details private: the client statements at "
        "the end of this record are for them to fill in and sign."
    )


def write_still_needed(pdf: RecordPdf) -> None:
    """Writes what the application needs besides this record, from the form's checklist."""
    pdf.write_heading("What your application still needs")
    for item in STILL_NEEDED:
        pdf.write_text(f"•  {item}")


def write_appendix(pdf: RecordPdf, jobs: list[RecordJob], photos: Mapping[str, bytes]) -> None:
    """Writes every confirmed job, then the before/after photos, as the form's appendix."""
    pdf.add_page()
    pdf.write_title("Appendix: scope of workplace exposure")
    pdf.write_note("Every confirmed job in this trade, oldest first, then before/after photos.")
    rows = [
        [
            format_date(job.done_on),
            job.trade_task,
            job.suburb,
            describe_confirmations({job.confirmed_via: 1}).removeprefix("1 "),
            str(len(job.photos)) if job.photos else "-",
        ]
        for job in jobs
    ]
    headings = ["Date", "Trade task", "Suburb", "Confirmed", "Photos"]
    pdf.write_table(headings, rows, APPENDIX_COLUMN_WIDTHS_MM)
    if any(job.photos for job in jobs):
        pdf.write_heading(
            "Before and after photos", room_needed_mm=PHOTO_ROW_MM + PHOTO_HEADING_ROOM_MM
        )
        shown_count = write_photo_pages(pdf, jobs, photos)
        if shown_count == 0:
            pdf.write_note("The photos are kept on Fixa and weren't included in this copy.")
