import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("verion.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RedactedAccessLogMiddleware(BaseHTTPMiddleware):
    """
    Logs one line per request without ever including the query string.

    SECURITY: several endpoints receive secrets as query parameters that
    must never reach logs - most importantly the GitHub OAuth callback
    (`?code=...&state=...`). uvicorn's default access log records the
    full request line including the query string, which would put a
    live (if short-lived, single-use) OAuth authorization code into
    stdout/log aggregation. This middleware is the replacement access
    log: it is intentionally path-only. The Dockerfile/CMD disables
    uvicorn's own access log (`--no-access-log`) so this is the only
    request logger in the stack, and no other logger in the app should
    log `request.url` (with query string) or the request body for
    auth/integration endpoints.
    """

    def __init__(self, app):
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started_at) * 1000, 1)

        # Read request_id if RequestIdMiddleware already set it; fall back
        # to the response header it sets, so this works regardless of
        # which middleware ends up wrapping which (Starlette's add_middleware
        # ordering semantics are easy to get backwards, so this is written
        # to not depend on it).
        request_id = (
            getattr(request.state, "request_id", None)
            or response.headers.get("X-Request-ID")
            or "-"
        )

        self._logger.info(
            "%s %s -> %s (%sms) [%s]",
            request.method,
            request.url.path,  # deliberately .path, never .url / query_params
            response.status_code,
            duration_ms,
            request_id,
        )

        return response
