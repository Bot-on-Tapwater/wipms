"""FastAPI application entry point.

Run locally with::

    uvicorn app.main:app --reload

Interactive API docs are served at ``/docs`` (Swagger) and ``/redoc``.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings, split_csv
from app.core.exceptions import AppError
from app.routers import (
    auth,
    labourers,
    metadata,
    payments,
    permissions,
    projects,
    reports,
    stats,
    users,
    works,
)

API_PREFIX = "/api/v1"

DESCRIPTION = """
Backend for **Ijenga** – bulk payment of construction labourers with full records.

**Authentication:** call `POST /api/v1/auth/login`, then click *Authorize* and paste
the `access_token`.

**Permissions:** every protected endpoint needs a permission code (shown in each
endpoint description as *Missing permission: ...* when denied). The frontend gets
the current user's codes from `GET /api/v1/permissions/me`.

**Payments are mocked** until the bank API is available.
"""

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=split_csv(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    """
    Turn business rule errors into ``{"detail": message}`` JSON responses.

    Args:
        request (Request): The incoming HTTP request.
        error (AppError): The raised business rule error.

    Returns:
        JSONResponse: ``{"detail": message}`` with the error's status code.
    """
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


@app.get("/health", tags=["Health"])
def health() -> dict:
    """
    Simple health check used by Docker and the reverse proxy.

    Returns:
        dict: ``{"status": "ok"}``.
    """
    return {"status": "ok"}


Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(permissions.router, prefix=API_PREFIX)
app.include_router(metadata.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(works.router, prefix=API_PREFIX)
app.include_router(labourers.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
