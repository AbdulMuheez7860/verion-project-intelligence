from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "bad_request",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    request_id: str | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"message": message, "code": code}
    if request_id:
        body["requestId"] = request_id
    return JSONResponse(status_code=status_code, content=body)


def get_request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None
