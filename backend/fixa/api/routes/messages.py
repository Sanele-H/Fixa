"""Translated chat for one job. The frontend polls GET every couple of seconds."""

from fastapi import APIRouter, status

from fixa.api.dependencies import (
    CurrentUserDependency,
    StoreDependency,
    TranslationPipelineDependency,
)
from fixa.domain.models import ApiModel, Message
from fixa.services import messages as message_service

router = APIRouter(tags=["messages"])


class NewMessage(ApiModel):
    """Request body for sending a chat message."""

    recipient_id: str
    text: str


@router.post("/jobs/{job_id}/messages", status_code=status.HTTP_201_CREATED)
def create_message(
    job_id: str,
    new_message: NewMessage,
    current_user: CurrentUserDependency,
    store: StoreDependency,
    translation_pipeline: TranslationPipelineDependency,
) -> Message:
    """Send a message. It is masked, checked for scams and translated before it is stored."""
    return message_service.send_message(
        store,
        translation_pipeline,
        current_user,
        job_id,
        new_message.recipient_id,
        new_message.text,
    )


@router.get("/jobs/{job_id}/messages")
def list_messages(
    job_id: str, with_user_id: str, current_user: CurrentUserDependency, store: StoreDependency
) -> list[Message]:
    """The conversation between the current user and `with_user_id` on this job."""
    return message_service.list_messages(store, current_user, job_id, with_user_id)
