"""The FastAPI app. Run everything with `npm run dev`, or only the API with `npm run dev:api`.

API docs: http://localhost:8000/docs

Every route in contracts/api.md exists and returns its fixture. Each is replaced with real code
behind the same shape, one area at a time.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, SQLModel

from fixa_api import (
    models,  # noqa: F401  (imported so its tables exist before create_all)
    safety,
)
from fixa_api.blocking import ProhibitedRequestError
from fixa_api.db import engine
from fixa_api.routes import (
    auth,
    chat,
    identity,
    jobs,
    lifecycle,
    notifications,
    off_app,
    photos,
    providers,
    records,
    reports,
    vouches,
)
from fixa_api.routes import safety as safety_routes
from fixa_api.sms import get_sms_sender

logger = logging.getLogger(__name__)
TIMER_SWEEP_SECONDS = 15


def sweep_safety_timers_once() -> None:
    """One sweep, with its own database session. Blocking: the database and the SMS call."""
    with Session(engine) as session:
        safety.sweep_missed_timers(session, get_sms_sender())


async def sweep_safety_timers_forever() -> None:
    """Every few seconds, text the trusted contact of anyone whose safety timer ran out. The sweep
    runs in a worker thread, so a slow database or SMS provider never holds up other requests."""
    while True:
        await asyncio.sleep(TIMER_SWEEP_SECONDS)
        try:
            await asyncio.to_thread(sweep_safety_timers_once)
        except Exception:  # the loop must keep going
            logger.exception("Safety timer sweep failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create any missing tables when the server starts (existing tables are left alone), and
    check safety timers in the background while it runs."""
    SQLModel.metadata.create_all(engine)
    sweeper = asyncio.create_task(sweep_safety_timers_forever())
    yield
    sweeper.cancel()


app = FastAPI(title="Fixa API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(ProhibitedRequestError)
def refuse_prohibited_request(_request: Request, refusal: ProhibitedRequestError) -> JSONResponse:
    """422 {"error": "prohibited_request", "category", "message"}: the contract's shape, with the
    reason and the legal route already in the person's language."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "prohibited_request",
            "category": refusal.category,
            "message": refusal.message,
        },
    )


for router_module in (
    auth,
    jobs,
    lifecycle,
    providers,
    chat,
    identity,
    off_app,
    photos,
    records,
    reports,
    vouches,
    notifications,
    safety_routes,
):
    app.include_router(router_module.router)


@app.get("/api/health")
def read_health() -> dict[str, str]:
    """Return {"status": "ok"}. Open it ten minutes before the pitch to wake the free server."""
    return {"status": "ok"}
