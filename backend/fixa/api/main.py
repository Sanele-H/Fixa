"""The FastAPI app. Run it with `npm run dev` from the repo root.

Interactive API docs (try every endpoint in the browser): http://localhost:8000/docs
Endpoints that aren't built yet answer 501 with the TODO that owns them.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fixa.api.routes import demo, jobs, messages, reference, users
from fixa.config import get_settings
from fixa.domain.job_states import InvalidJobTransitionError
from fixa.services.errors import NotFoundError, PermissionDeniedError

API_PREFIX = "/api"

STATUS_CODES_BY_ERROR_TYPE: dict[type[Exception], int] = {
    NotImplementedError: status.HTTP_501_NOT_IMPLEMENTED,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    InvalidJobTransitionError: status.HTTP_409_CONFLICT,
}


def create_app() -> FastAPI:
    """Build the app: CORS, error mapping and every router under /api."""
    app = FastAPI(title="Fixa API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    for router in (reference.router, users.router, jobs.router, messages.router, demo.router):
        app.include_router(router, prefix=API_PREFIX)
    return app


def register_error_handlers(app: FastAPI) -> None:
    """Turn service errors into HTTP responses so routes don't need try/except."""
    for error_type, status_code in STATUS_CODES_BY_ERROR_TYPE.items():
        app.add_exception_handler(error_type, create_error_handler(status_code))


def create_error_handler(status_code: int):
    """Return a handler that answers `status_code` with the error's message as `detail`."""

    async def handle_error(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return handle_error


app = create_app()
