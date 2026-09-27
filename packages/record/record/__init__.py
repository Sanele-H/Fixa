"""Work record and ARPL export for Fixa (P4).

Owner: P4. Only P4 edits files in packages/record/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    build_record(evidence, mode, *, verify_base_url=None, photos=None)
        -> RecordDoc(pdf_bytes, verify_code, sha256)
        mode: "arpl" | "statement". The two keyword arguments were added in step 6 and are
        optional, so build_record(evidence, mode) still works.
    verify_record(verify_code, stored) -> VerifyResult

Exports never include customers' names, phone numbers or addresses. The ARPL record
follows the sections of the merSETA ARPL Trade Test Application Form (LPM-FM-009) and
never claims that anyone qualifies.
"""

from record.experience import ARPL_TRADE_TITLES, ARPL_TRADES, ArplTradeError
from record.export import build_record, verify_record
from record.models import (
    RecordDoc,
    RecordEvidence,
    RecordJob,
    RecordPhoto,
    StoredRecord,
    VerifyResult,
    Vouch,
)

__all__ = [
    "ARPL_TRADES",
    "ARPL_TRADE_TITLES",
    "ArplTradeError",
    "RecordDoc",
    "RecordEvidence",
    "RecordJob",
    "RecordPhoto",
    "StoredRecord",
    "VerifyResult",
    "Vouch",
    "build_record",
    "verify_record",
]
