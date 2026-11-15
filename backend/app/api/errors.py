"""Structured API error responses. Internal traces stay in logs."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    CatalogError,
    ExplanationError,
    ProviderError,
    PulseIQError,
)
from app.schemas.api import ErrorResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CatalogError)
    async def catalog_error(_request: Request, exc: CatalogError) -> JSONResponse:
        return _error(exc.status_code, str(exc), exc.code)

    @app.exception_handler(ProviderError)
    async def provider_error(_request: Request, exc: ProviderError) -> JSONResponse:
        request_id = _request_id()
        logger.warning("provider error code=%s request_id=%s", exc.code, request_id)
        return _error(exc.status_code, str(exc), exc.code, exc.detail, request_id)

    @app.exception_handler(ExplanationError)
    async def explanation_error(
        _request: Request, exc: ExplanationError
    ) -> JSONResponse:
        request_id = _request_id()
        logger.warning("explanation error code=%s request_id=%s", exc.code, request_id)
        return _error(exc.status_code, str(exc), exc.code, exc.detail, request_id)

    @app.exception_handler(PulseIQError)
    async def domain_error(_request: Request, exc: PulseIQError) -> JSONResponse:
        logger.warning("domain error: %s", exc)
        return _error(400, str(exc), "domain_error")

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", ()))
            messages.append(f"{location}: {item.get('msg')}")
        detail = "; ".join(messages) if messages else "request validation failed"
        return _error(
            422, "Request validation failed", "validation_error", detail, _request_id()
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request failed"
        code = "not_found" if exc.status_code == 404 else "http_error"
        return _error(exc.status_code, detail, code, request_id=_request_id())

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled API error")
        return _error(
            500, "Internal server error", "internal_error", request_id=_request_id()
        )


def _request_id() -> str:
    return uuid.uuid4().hex[:12]


def _error(
    status_code: int,
    error: str,
    code: str,
    detail: str | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=error, code=code, detail=detail, request_id=request_id)
    return JSONResponse(status_code=status_code, content=body.model_dump())
