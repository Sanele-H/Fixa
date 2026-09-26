"""Demo users: pick who you are on each phone, and change your language."""

from fastapi import APIRouter

from fixa.api.dependencies import CurrentUserDependency, StoreDependency
from fixa.domain.models import ApiModel, User

router = APIRouter(tags=["users"])


class UserLanguageUpdate(ApiModel):
    """Request body for changing your preferred language."""

    preferred_language: str


@router.get("/users")
def list_users(store: StoreDependency) -> list[User]:
    """Return every demo user (no contact details), for the "who are you?" screen."""
    return store.list_users()


@router.get("/users/me")
def read_current_user(current_user: CurrentUserDependency) -> User:
    """Return the user named in the X-User-Id header."""
    return current_user


@router.patch("/users/me")
def update_current_user_language(
    update: UserLanguageUpdate, current_user: CurrentUserDependency, store: StoreDependency
) -> User:
    """Change the current user's preferred language.

    TODO (Role 3): reject codes that fixa.translation.languages doesn't support.
    """
    updated_user = current_user.model_copy(update={"preferred_language": update.preferred_language})
    return store.update_user(updated_user)
