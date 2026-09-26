"""Work record and ARPL export for Fixa (P4).

Owner: P4. Only P4 edits files in packages/record/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    build_record(evidence, mode) -> RecordDoc(pdf_bytes, verify_code, sha256)
        mode: "arpl" | "statement"
    verify_record(verify_code, stored) -> VerifyResult

Exports never include customers' names, phone numbers or addresses.

Step 0 (Day 1): stubs with the correct return types, so the API can import them.
The input and output shapes are in record.models and are exported here.
"""

from record.export import ARPL_TRADES, ArplTradeError, build_record, verify_record
from record.models import (
    RecordDoc,
    RecordEvidence,
    RecordJob,
    StoredRecord,
    VerifyResult,
)

__all__ = [
    "ARPL_TRADES",
    "ArplTradeError",
    "RecordDoc",
    "RecordEvidence",
    "RecordJob",
    "StoredRecord",
    "VerifyResult",
    "build_record",
    "verify_record",
]
