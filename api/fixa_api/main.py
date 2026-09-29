"""The FastAPI app. Run everything with `npm run dev`, or only the API with `npm run dev:api`.

API docs: http://localhost:8000/docs

Every route in contracts/api.md exists and returns its fixture. Each is replaced with real code
behind the same shape, one area at a time.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import SQLModel

from fixa_api import models  # noqa: F401  (imported so its tables exist before create_all)
from fixa_api.db import engine
from fixa_api.routes import auth, chat, identity, jobs, off_app, providers, records


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create any missing tables when the server starts. Existing tables are left alone."""
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title="Fixa API", version="0.1.0", lifespan=lifespan)

for router_module in (auth, jobs, providers, chat, identity, off_app, records):
    app.include_router(router_module.router)


@app.get("/api/health")
def read_health() -> dict[str, str]:
    """Return {"status": "ok"}. Open it ten minutes before the pitch to wake the free server."""
    return {"status": "ok"}
