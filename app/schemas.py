"""Pydantic v2 request/response schemas.

These models are intentionally framework-agnostic so they can be used by both the
existing Flask application and the FastAPI parity layer during the incremental
migration.

Migration guidance:
- Keep request/response shapes stable for golden-master contract tests.
- Avoid introducing behavioral changes here; the schemas should reflect the
  current API contract while the route implementation is cut over slice by slice.
- Preserve database and payload compatibility until parity is proven.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base model configured for strict API boundary usage."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


class ErrorDetail(APIModel):
    """Standardized error detail for validation and application errors."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(default=None, description="Optional field path related to the error")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional structured error context")


class ErrorResponse(APIModel):
    """Standard error response envelope."""

    error: ErrorDetail


class HealthResponse(APIModel):
    """Basic health check response."""

    status: str = Field(default="ok", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response generation time")


class IDResponse(APIModel):
    """Generic response containing a generated identifier."""

    id: UUID


class MessageResponse(APIModel):
    """Generic message response."""

    message: str


T = TypeVar("T")


class PaginatedResponse(APIModel, Generic[T]):
    """Generic paginated response envelope."""

    items: list[T] = Field(default_factory=list)
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)


class PaginationParams(APIModel):
    """Common pagination query parameters."""

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class TimestampedRequest(APIModel):
    """Base request model for payloads with optional client timestamp metadata."""

    request_id: UUID | None = Field(default=None, description="Client-provided request identifier")
    requested_at: datetime | None = Field(default=None, description="Client-provided request timestamp")


class TimestampedResource(APIModel):
    """Base response/resource model with audit fields commonly shared by APIs."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None


__all__ = [
    "APIModel",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "IDResponse",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationParams",
    "TimestampedRequest",
    "TimestampedResource",
]
