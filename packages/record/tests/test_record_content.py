"""What the records say: the experience maths, the form's sections, statements and photos.

The embedded font stores text as glyph ids, so these tests read the PDF's text_log.
"""

import io
import re
from datetime import date, timedelta

import pytest
from PIL import Image

from record import RecordEvidence, RecordJob, RecordPhoto, Vouch, summarise_arpl_experience
from record.client_statements import MAX_CLIENT_STATEMENTS, choose_statement_jobs
from record.experience import (
    count_whole_months,
    format_duration,
    group_jobs_by_task,
    summarise_experience,
)
from record.export import render_record
from record.pdf_layout import find_dark_runs
from record.sections import RecordCover

COVER = RecordCover(
    verify_code="FX7K2Q", sha256="0" * 64, issued_on=date(2026, 9, 29), verify_url=None
)
FIRST_DAY = date(2022, 9, 30)
QUALIFYING_CLAIM = re.compile(r"\b(you qualify|qualifies|qualified|is eligible)\b", re.IGNORECASE)


def make_job(done_on: date, trade_task: str = "Unblock drain", **fields) -> RecordJob:
    """Makes a confirmed plumbing job on a given day; any other RecordJob field can be passed."""
    job_fields = {"suburb": "Yeoville", "trade": "plumbing", "confirmed_via": "sms"}
    return RecordJob(done_on=done_on, trade_task=trade_task, **{**job_fields, **fields})


def make_evidence(jobs: list[RecordJob], **fields) -> RecordEvidence:
    """Makes a plumber's record with the given jobs."""
    return RecordEvidence(
        provider_id="prov_003", display_name="Nosipho", trades=["plumbing"], jobs=jobs, **fields
    )


def render_text(evidence: RecordEvidence, mode: str, photos=None) -> str:
    """Renders a record and returns all of its text, one piece per line."""
    return "\n".join(render_record(evidence, mode, COVER, photos or {}).text_log)


def make_jpeg() -> bytes:
    """Makes a small JPEG, as a phone photo would arrive."""
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), (40, 110, 160)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_whole_months_only_count_once_the_day_is_reached():
    assert count_whole_months(date(2022, 9, 30), date(2022, 10, 29)) == 0
    assert count_whole_months(date(2022, 9, 30), date(2026, 9, 30)) == 48


@pytest.mark.parametrize(
    ("months", "text"),
    [(0, "0 months"), (1, "1 month"), (12, "1 year"), (47, "3 years 11 months")],
)
def test_durations_read_naturally(months, text):
    assert format_duration(months) == text


def test_experience_counts_the_span_and_the_months_with_work():
    jobs = [make_job(FIRST_DAY), make_job(date(2023, 1, 5)), make_job(date(2026, 9, 29))]
    summary = summarise_experience(jobs)
    assert (summary.first_job_on, summary.last_job_on) == (FIRST_DAY, date(2026, 9, 29))
    assert (summary.span_months, summary.months_with_work, summary.calendar_months) == (47, 3, 49)


def test_details_of_experience_has_one_row_per_task_with_its_dates():
    jobs = [
        make_job(date(2023, 1, 5), "Fix dripping tap"),
        make_job(date(2024, 6, 1), "Unblock drain", confirmed_via="app"),
        make_job(date(2025, 2, 3), "Unblock drain", suburb="Berea"),
    ]
    rows = group_jobs_by_task(jobs)
    assert [row.trade_task for row in rows] == ["Unblock drain", "Fix dripping tap"]
    assert (rows[0].first_done_on, rows[0].last_done_on, rows[0].job_count) == (
        date(2024, 6, 1),
        date(2025, 2, 3),
        2,
    )
    assert rows[0].suburbs == ["Berea", "Yeoville"]
    assert rows[0].confirmation_counts == {"app": 1, "sms": 1}


def test_arpl_record_follows_the_form_and_never_claims_anyone_qualifies():
    text = render_text(make_evidence([make_job(FIRST_DAY), make_job(date(2026, 9, 1))]), "arpl")
    for section in [
        "merSETA ARPL Trade Test Application Form (LPM-FM-009)",
        "Trade test applying for (trade title): Plumber",
        "Details of experience (form page 3)",
        "What your application still needs",
        "Appendix: scope of workplace exposure",
        "It is not a qualification",
    ]:
        assert section in text
    assert not QUALIFYING_CLAIM.search(text)


def test_arpl_record_covers_only_the_chosen_trade():
    jobs = [make_job(FIRST_DAY), make_job(FIRST_DAY, trade_task="Rewire room")]
    jobs[1] = jobs[1].model_copy(update={"trade": "electrical"})
    evidence = make_evidence(jobs).model_copy(update={"trades": ["plumbing", "electrical"]})
    text = render_text(evidence.model_copy(update={"arpl_trade": "plumbing"}), "arpl")
    assert "Unblock drain" in text and "Rewire room" not in text


def test_vouches_show_suburb_and_date_but_never_a_phone_number():
    vouch = Vouch(text="Fixed it fast, call 082 555 1234.", suburb="Berea", given_on=FIRST_DAY)
    text = render_text(make_evidence([make_job(FIRST_DAY)], vouches=[vouch]), "arpl")
    assert "[number hidden]" in text and "555 1234" not in text
    assert "Customer in Berea, 30/09/2022" in text


def test_client_statements_are_only_for_references_and_spread_over_time():
    jobs = [
        make_job(FIRST_DAY + timedelta(days=30 * index), reference_agreed=index % 2 == 0)
        for index in range(30)
    ]
    chosen = choose_statement_jobs(jobs)
    references = [job for job in jobs if job.reference_agreed]
    assert len(chosen) == MAX_CLIENT_STATEMENTS
    assert all(job.reference_agreed for job in chosen)
    assert (chosen[0], chosen[-1]) == (references[0], references[-1])


def test_no_client_statement_without_a_reference():
    text = render_text(make_evidence([make_job(FIRST_DAY)]), "arpl")
    assert "Client statement" not in text


def test_client_statement_leaves_the_customers_details_blank():
    text = render_text(make_evidence([make_job(FIRST_DAY, reference_agreed=True)]), "arpl")
    assert "Client statement" in text and "Commissioner of Oaths" in text
    assert "Full names and surname" in text and "ID or passport number" in text


def test_photos_are_shown_when_their_bytes_are_passed_in():
    photos = [
        RecordPhoto(photo_id="p_before", kind="before"),
        RecordPhoto(photo_id="p_after", kind="after"),
    ]
    evidence = make_evidence([make_job(FIRST_DAY, photos=photos)])
    with_bytes = render_text(evidence, "arpl", {"p_before": make_jpeg(), "p_after": make_jpeg()})
    without_bytes = render_text(evidence, "arpl")
    assert "30/09/2022 · Unblock drain · Yeoville" in with_bytes
    assert "The photos are kept on Fixa and weren't included in this copy." in without_bytes


def test_unreadable_photo_bytes_are_skipped_not_fatal():
    evidence = make_evidence(
        [make_job(FIRST_DAY, photos=[RecordPhoto(photo_id="p", kind="after")])]
    )
    assert "weren't included" in render_text(evidence, "arpl", {"p": b"not an image"})


def test_names_in_any_south_african_language_print():
    evidence = make_evidence([make_job(FIRST_DAY)]).model_copy(
        update={"display_name": "Ṱhanyani Ŋ."}
    )
    assert "Ṱhanyani Ŋ." in render_text(evidence, "statement")


def test_statement_is_labelled_and_never_shows_an_invented_amount():
    jobs = [
        make_job(date(2026, 7, 1), amount_rands=1250),
        make_job(date(2026, 7, 9), amount_rands=None, confirmed_via="ussd"),
        make_job(date(2026, 8, 2), amount_rands=None),
    ]
    text = render_text(make_evidence(jobs), "statement")
    assert "Customer-confirmed, not a bank statement" in text
    assert "R1 250" in text and "By customer USSD" in text
    assert text.count("not recorded") == 3  # two jobs, and August's month total
    assert "R0" not in text


def test_qr_rows_become_runs_of_dark_modules():
    assert find_dark_runs([True, True, False, True, False, False, True]) == [(0, 2), (3, 1), (6, 1)]
    assert find_dark_runs([False, False]) == []


def make_record_for_trades(jobs: list[RecordJob], trades: list[str]) -> RecordEvidence:
    """A record like make_evidence's, for a provider with the given trades."""
    return RecordEvidence(provider_id="prov_003", display_name="Nosipho", trades=trades, jobs=jobs)


def test_arpl_experience_counts_the_arpl_trade_only():
    plumbing_jobs = [make_job(FIRST_DAY), make_job(FIRST_DAY + timedelta(days=400))]
    painting_job = make_job(FIRST_DAY - timedelta(days=900), trade="painting")
    evidence = make_record_for_trades([*plumbing_jobs, painting_job], ["plumbing", "painting"])

    experience = summarise_arpl_experience(evidence)

    assert experience.arpl_trade == "plumbing"
    assert experience.summary == summarise_experience(plumbing_jobs)


def test_arpl_experience_without_an_arpl_trade_counts_every_job():
    jobs = [
        make_job(FIRST_DAY, trade="painting"),
        make_job(FIRST_DAY + timedelta(days=90), trade="painting"),
    ]
    evidence = make_record_for_trades(jobs, ["painting"])

    experience = summarise_arpl_experience(evidence)

    assert experience.arpl_trade is None
    assert experience.summary == summarise_experience(jobs)
