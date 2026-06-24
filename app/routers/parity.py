"""Parity router for incremental Flask-to-FastAPI migration.

This module is intentionally thin: it provides a FastAPI router that can sit
in front of existing application behavior while a migration is validated via
contract tests and slice-by-slice cutover.

Migration strategy supported by this layer:
1. Golden-master contract tests lock current Flask behavior.
2. Dependencies are upgraded without changing observable behavior.
3. This parity layer mirrors existing request/response semantics.
4. Individual routes are migrated one slice at a time.
5. Database schema remains unchanged until parity is proven.

The router is designed to be safe to mount early in the migration. It exposes
health/metadata endpoints and a generic compatibility endpoint that can be used
by tests or adapters without coupling to a specific database or business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field


router = APIRouter(prefix="/parity", tags=["parity"])


MIGRATION_PHASES: List[str] = [
    "golden_master_contract_tests",
    "dependency_upgrade",
    "parity_api_layer",
    "slice_by_slice_cutover",
    "schema_preservation_until_parity",
]


@dataclass(frozen=True)
class ParityStatus:
    """Simple status payload describing the migration posture."""

    service: str = "parity-layer"
    status: str = "ok"
    mode: str = "migration"
    migration_plan: List[str] = None  # type: ignore[assignment]
    timestamp_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if payload["migration_plan"] is None:
            payload["migration_plan"] = MIGRATION_PHASES
        if not payload["timestamp_utc"]:
            payload["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        return payload


class ParityEchoRequest(BaseModel):
    """Echo request used to validate request/response parity in tests."""

    method: str = Field(..., description="HTTP method to echo back")
    path: str = Field(..., description="Request path to echo back")
    headers: Dict[str, str] = Field(default_factory=dict)
    query: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None)


class ParityEchoResponse(BaseModel):
    """Echo response that preserves input for contract verification."""

    ok: bool = True
    echoed: ParityEchoRequest


@router.get("/health", summary="Parity health check")
async def health() -> Dict[str, Any]:
    """Health endpoint for readiness checks during migration."""

    return ParityStatus().to_dict()


@router.get("/plan", summary="Migration plan metadata")
async def plan() -> Dict[str, Any]:
    """Return the current migration plan and sequencing."""

    return {
        "migration_plan": MIGRATION_PHASES,
        "current_phase": "parity_api_layer",
        "preserve_behavior": True,
        "preserve_schema": True,
    }


@router.post("/echo", response_model=ParityEchoResponse, summary="Contract-test echo")
async def echo(payload: ParityEchoRequest) -> ParityEchoResponse:
    """Echo endpoint to support golden-master contract tests.

    This endpoint should remain stable while the underlying Flask routes are
    incrementally replaced.
    """

    return ParityEchoResponse(echoed=payload)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], summary="Compatibility fallback")
async def compatibility_fallback(request: Request, path: str) -> Response:
    """Fallback route for unmigrated slices.

    During the migration window, this endpoint intentionally returns a clear
    501 response for paths that have not yet been cut over. It avoids changing
    the database schema or executing business logic for routes that are still
    owned by Flask, while making the unsupported surface explicit.

    Once a slice is migrated, mount the new FastAPI route above this fallback
    or remove the corresponding path from the legacy Flask layer.
    """

    supported_paths = {"health", "plan", "echo"}
    if path in supported_paths:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Method not allowed on parity endpoint.",
        )

    content = {
        "ok": False,
        "path": f"/{path}",
        "method": request.method,
        "message": (
            "Route not yet migrated to FastAPI parity layer. "
            "Keep using the existing Flask implementation until contract tests pass."
        ),
        "migration_plan": MIGRATION_PHASES,
    }
    return Response(
        content=ParityStatus().to_dict().__repr__() + "\n" + str(content),
        media_type="application/json",
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
    )


__all__ = ["router", "MIGRATION_PHASES", "ParityEchoRequest", "ParityEchoResponse", "ParityStatus"]
