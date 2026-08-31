"""Map exceptions to the section-24 error envelope.

Unhandled exceptions never include stack traces or internal messages in the response body.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.exceptions import AppError
from app.common.responses import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.errors")

_HTTP_STATUS_TO_CODE = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    409: "RESOURCE_ALREADY_EXISTS",
    422: "VALIDATION_ERROR",
}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(422, "VALIDATION_ERROR", "Request validation failed")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = _HTTP_STATUS_TO_CODE.get(exc.status_code, "REQUEST_FAILED")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", type(exc).__name__)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
