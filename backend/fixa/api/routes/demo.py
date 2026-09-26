"""Demo helpers. Use between rehearsals so every run starts from the same state."""

from fastapi import APIRouter, status

from fixa.api.dependencies import StoreDependency

router = APIRouter(tags=["demo"])


@router.post("/demo/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_demo(store: StoreDependency) -> None:
    """Delete all jobs, quotes and messages and reload the seeded demo users."""
    store.reset_to_demo_data()
