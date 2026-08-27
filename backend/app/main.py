import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai_assistant, analysis, analysis_runs, analytics, audit_logs, auth, findings, integrations, notifications, organization, pull_requests, repositories, reports, webhooks
from app.core.config import get_settings
from app.core.database import close_client, get_database
from app.core.errors import AppError, error_response, get_request_id
from app.core.health import readiness_report
from app.core.indexes import ensure_indexes
from app.core.middleware import RedactedAccessLogMiddleware, RequestIdMiddleware
from app.core.redis import close_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.validate_for_startup()
    db = get_database()
    await db.command("ping")
    await ensure_indexes(db)
    yield
    await close_client()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RedactedAccessLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return error_response(
            status_code=exc.status_code,
            message=exc.message,
            code=exc.code,
            request_id=get_request_id(request),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else str(detail)
        code = "http_error"
        if exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        elif exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 409:
            code = "conflict"
        elif exc.status_code == 422:
            code = "validation_error"
        elif exc.status_code == 429:
            code = "rate_limited"
        return error_response(
            status_code=exc.status_code,
            message=message,
            code=code,
            request_id=get_request_id(request),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"request_id": get_request_id(request)})
        return error_response(
            status_code=500,
            message="An unexpected error occurred.",
            code="internal_error",
            request_id=get_request_id(request),
        )

    api_prefix = settings.api_v1_prefix
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(organization.router, prefix=api_prefix)
    app.include_router(audit_logs.router, prefix=api_prefix)
    app.include_router(notifications.router, prefix=api_prefix)
    app.include_router(integrations.router, prefix=api_prefix)
    app.include_router(repositories.router, prefix=api_prefix)
    app.include_router(analysis_runs.router, prefix=api_prefix)
    app.include_router(pull_requests.router, prefix=api_prefix)
    app.include_router(analysis.router, prefix=api_prefix)
    app.include_router(findings.router, prefix=api_prefix)
    app.include_router(analytics.router, prefix=api_prefix)
    app.include_router(ai_assistant.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)
    app.include_router(webhooks.router, prefix=api_prefix)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/ready")
    async def ready() -> JSONResponse:
        report = await readiness_report()
        status_code = 200 if report["status"] == "ready" else 503
        return JSONResponse(report, status_code=status_code)

    @app.get(f"{api_prefix}/health")
    async def api_health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return app


app = create_app()
