"""The FastAPI app. Run everything with `npm run dev`, or only the API with `npm run dev:api`.

API docs: http://localhost:8000/docs

This is the starting shell: only /api/health exists. P2's Day 1 task is to make every route in
contracts/api.md return its fixture, then replace each with real code behind the same shape.
"""

from fastapi import FastAPI

app = FastAPI(title="Fixa API", version="0.1.0")


@app.get("/api/health")
def read_health() -> dict[str, str]:
    """Return {"status": "ok"}. Open it ten minutes before the pitch to wake the free server."""
    return {"status": "ok"}
