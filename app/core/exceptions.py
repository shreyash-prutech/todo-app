"""Compatibility exception handlers and response shims.

This module provides a small, framework-agnostic exception layer that helps
bridge a Flask-to-FastAPI migration without changing the outward contract too
quickly. It keeps response shapes stable, emits JSON payloads that are friendly
for both legacy and new clients, and can be wired into either Flask or FastAPI
apps.

Migration posture supported by this module:
1. Golden-master contract tests validate current behavior.
2. Dependency upgrades can happen independently of route semantics.
3. A parity API layer can reuse these handlers to preserve response formats.
4. Slice-by-slice route cutover can continue while keeping database schema and
   current behavior stable until parity is proven.
"""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Tuple, Type, Union

try:  # pragma: no cover - Flask is optional during migration.
    from flask import jsonify as flask_jsonify  # type: ignore
except Exception:  # pragma: no cover
    flask_jsonify = None

try:  # pragma: no cover - FastAPI/Starlette is optional during migration.
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover
    FastAPI = Any  # type: ignore
    Request = Any  # type: ignore
    JSONResponse = Any  # type: ignore


@dataclass
class APIError(Exception):
    """Base application error with HTTP semantics."""

    message: str
    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error: str = "internal_server_error"
    details: Optional[Mapping[str, Any]] = None

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "error": self.error,
            "message": self.message,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload


@dataclass
class ValidationError(APIError):
    """Represents a 4xx validation/contract violation."""

    status_code: int = HTTPStatus.BAD_REQUEST
    error: str = "validation_error"


@dataclass
class NotFoundError(APIError):
    """Represents a missing resource."""

    status_code: int = HTTPStatus.NOT_FOUND
    error: str = "not_found"


@dataclass
class ConflictError(APIError):
    """Represents a conflict with current state."""

    status_code: int = HTTPStatus.CONFLICT
    error: str = "conflict"


@dataclass
class ServiceUnavailableError(APIError):
    """Represents a temporary upstream or maintenance outage."""

    status_code: int = HTTPStatus.SERVICE_UNAVAILABLE
    error: str = "service_unavailable"


class CompatibilityResponseShim:
    """Builds framework-specific JSON responses while preserving payload shape."""

    @staticmethod
    def build_payload(
        message: str,
        *,
        error: str,
        status_code: int,
        details: Optional[Mapping[str, Any]] = None,
        legacy_message_key: str = "message",
        legacy_error_key: str = "error",
        include_status_code: bool = True,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            legacy_error_key: error,
            legacy_message_key: message,
        }
        if details:
            payload["details"] = dict(details)
        if include_status_code:
            payload["status_code"] = int(status_code)
        return payload

    @staticmethod
    def flask_response(payload: Mapping[str, Any], status_code: int):
        if flask_jsonify is None:  # pragma: no cover - defensive fallback
            return payload, status_code
        response = flask_jsonify(dict(payload))
        response.status_code = int(status_code)
        return response

    @staticmethod
    def fastapi_response(payload: Mapping[str, Any], status_code: int):
        return JSONResponse(content=dict(payload), status_code=int(status_code))


class ExceptionHandlerRegistry:
    """Registry that can wire the same exception behavior into Flask or FastAPI."""

    def __init__(self) -> None:
        self._handlers: MutableMapping[Type[BaseException], Callable[[BaseException], Any]] = {}

    def register(
        self,
        exc_type: Type[BaseException],
        handler: Callable[[BaseException], Any],
    ) -> None:
        self._handlers[exc_type] = handler

    def handle(self, exc: BaseException) -> Any:
        for registered_type, handler in self._handlers.items():
            if isinstance(exc, registered_type):
                return handler(exc)
        return self.handle_unexpected(exc)

    @staticmethod
    def handle_api_error(exc: APIError) -> Dict[str, Any]:
        return CompatibilityResponseShim.build_payload(
            exc.message,
            error=exc.error,
            status_code=int(exc.status_code),
            details=exc.details,
        )

    @staticmethod
    def handle_unexpected(exc: BaseException) -> Dict[str, Any]:
        return CompatibilityResponseShim.build_payload(
            "An unexpected error occurred.",
            error="internal_server_error",
            status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
            details={"exception_type": exc.__class__.__name__},
        )


registry = ExceptionHandlerRegistry()
registry.register(APIError, registry.handle_api_error)


def build_error_response(
    exc: Union[BaseException, APIError],
    *,
    framework: str = "fastapi",
):
    """Return a framework-specific JSON error response.

    Args:
        exc: Exception instance to convert.
        framework: Either "fastapi" or "flask".

    Returns:
        A FastAPI JSONResponse, a Flask response, or a tuple fallback.
    """
    payload = registry.handle(exc)
    status_code = int(payload.get("status_code", HTTPStatus.INTERNAL_SERVER_ERROR))

    if framework.lower() == "flask":
        return CompatibilityResponseShim.flask_response(payload, status_code)
    return CompatibilityResponseShim.fastapi_response(payload, status_code)


def install_flask_exception_handlers(app: Any) -> Any:
    """Register compatibility handlers on a Flask app.

    The app only needs to provide errorhandler registration. This keeps the
    module usable during migration when app construction may differ between
    services.
    """

    @app.errorhandler(APIError)
    def _handle_api_error(exc: APIError):  # pragma: no cover - integration path
        return build_error_response(exc, framework="flask")

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):  # pragma: no cover - integration path
        return build_error_response(exc, framework="flask")

    return app


def install_fastapi_exception_handlers(app: Any) -> Any:
    """Register compatibility handlers on a FastAPI app."""

    @app.exception_handler(APIError)
    async def _handle_api_error(request: Request, exc: APIError):  # pragma: no cover - integration path
        return build_error_response(exc, framework="fastapi")

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):  # pragma: no cover - integration path
        return build_error_response(exc, framework="fastapi")

    return app


__all__ = [
    "APIError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ServiceUnavailableError",
    "CompatibilityResponseShim",
    "ExceptionHandlerRegistry",
    "build_error_response",
    "install_flask_exception_handlers",
    "install_fastapi_exception_handlers",
    "registry",
]
