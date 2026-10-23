"""Consistent error envelope: {"error": {code, message, field?, request_id}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.state_machine import InvalidTransition


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        field: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.field = field
        if status_code:
            self.status_code = status_code
        self.extra = extra or {}


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailure(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"


def _envelope(
    request: Request, code: str, message: str, field: str | None = None, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": getattr(request.state, "request_id", None),
    }
    if field:
        body["field"] = field
    if extra:
        body.update(extra)
    return {"error": body}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(request, exc.code, exc.message, exc.field, exc.extra),
        )

    @app.exception_handler(InvalidTransition)
    async def handle_invalid_transition(request: Request, exc: InvalidTransition) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=_envelope(
                request,
                "INVALID_STATE_TRANSITION",
                str(exc),
                extra={"current": exc.current, "target": exc.target, "allowed": exc.allowed},
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = [str(p) for p in first.get("loc", []) if p != "body"]
        return JSONResponse(
            status_code=422,
            content=_envelope(
                request,
                "VALIDATION_FAILED",
                first.get("msg", "Invalid request"),
                field=".".join(loc) or None,
                extra={
                    "errors": [
                        {
                            "field": ".".join(str(p) for p in e.get("loc", []) if p != "body"),
                            "message": e.get("msg"),
                        }
                        for e in exc.errors()
                    ]
                },
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces or internals to clients.
        return JSONResponse(
            status_code=500,
            content=_envelope(request, "INTERNAL_ERROR", "An unexpected error occurred."),
        )
