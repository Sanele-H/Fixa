"""Chat use cases. Owner: Role 3, calling Role 1's translation pipeline.

The order of the message pipeline matters:
    1. mask_contact_details   (safety/contact_masking.py - raw numbers are never stored)
    2. find_scam_warnings     (safety/scam_warnings.py)
    3. pipeline.translate     (translation/pipeline.py - into the recipient's language)
    4. store.create_message
"""

from fixa.domain.models import Message, User
from fixa.storage.memory_store import MemoryStore
from fixa.translation.pipeline import TranslationPipeline


def send_message(
    store: MemoryStore,
    translation_pipeline: TranslationPipeline,
    sender: User,
    job_id: str,
    recipient_id: str,
    text: str,
) -> Message:
    """Mask, check, translate and store one message between the two sides of a job.

    TODO (Role 3, Day 3-4): implement the pipeline above. Check the sender and recipient
    are the job's customer and one of its shortlisted providers.
    """
    raise NotImplementedError("TODO Role 3: send_message")


def list_messages(
    store: MemoryStore, viewer: User, job_id: str, other_user_id: str
) -> list[Message]:
    """Return the conversation between `viewer` and `other_user_id` on one job, oldest first.

    The frontend polls this every couple of seconds; keep it fast.
    """
    raise NotImplementedError("TODO Role 3: list_messages")
