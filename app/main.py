"""FastAPI application skeleton for incremental Flask-to-FastAPI migration.

This module intentionally starts as a thin, production-friendly FastAPI app
that can coexist with an existing Flask application during migration.

Migration strategy encoded here:
1. Keep current behavior and database schema stable.
2. Add golden-master contract tests against the existing Flask API.
3. Upgrade dependencies in a controlled manner.
4. Introduce a FastAPI parity layer that mirrors existing endpoints.
5. Cut over routes slice-by-slice only after parity is proven.

The app exposes:
- /healthz: lightweight liveness check
- /readyz: readiness check for deployment orchestration
- /migration/status: migration guidance and current posture

To integrate new FastAPI routes, import and include routers below once parity is
validated. This file avoids making assumptions about the legacy Flask app or
schema so the current system behavior remains preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_NAME = "FastAPI Migration Skeleton"
APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class MigrationPhase:
    """Represents the recommended migration sequence."""

    name: str
    description: str
    done_when: str


MIGRATION_PLAN: List[MigrationPhase] = [
    MigrationPhase(
        name="golden_master_contract_tests",
        description=(
            "Capture the current Flask API behavior with golden-master contract tests "
            "to prevent regressions while migrating."
        ),
        done_when=(
            "Critical endpoints are covered by contract tests and pass consistently "
            "against the legacy Flask implementation."
        ),
    ),
    MigrationPhase(
        name="dependency_upgrade",
        description=(
            "Upgrade shared dependencies incrementally, validating runtime compatibility "
            "and test stability at each step."
        ),
        done_when=(
            "Dependency upgrades are complete and the application remains behaviorally "
            "equivalent under the contract test suite."
        ),
    ),
    MigrationPhase(
        name="parity_api_layer",
        description=(
            "Introduce a FastAPI parity layer that mirrors the Flask API surface while "
            "preserving request/response semantics."
        ),
        done_when=(
            "FastAPI endpoints match the legacy API contract for all migrated slices."
        ),
    ),
    MigrationPhase(
        name="slice_by_slice_cutover",
        description=(
            "Move routes one slice at a time from Flask to FastAPI after each slice's "
            "parity is proven in contract tests."
        ),
        done_when=(
            "All routes are served by FastAPI and the Flask app is fully retired."
        ),
    ),
]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    The application is intentionally minimal to support a low-risk migration.
    CORS is enabled with conservative defaults that can be tightened later via
    environment-specific settings.
    """

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["ops"])
    async def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["ops"])
    async def readyz() -> Dict[str, str]:
        return {"status": "ready"}

    @app.get("/migration/status", tags=["migration"])
    async def migration_status() -> Dict[str, Any]:
        return {
            "application": APP_NAME,
            "version": APP_VERSION,
            "phase": "incremental_flask_to_fastapi_migration",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "preservation_guarantees": {
                "behavior": "Current behavior is preserved until contract parity is proven.",
                "schema": "Database schema remains unchanged during the migration.",
                "cutover": "Routes are migrated slice-by-slice only after parity validation.",
            },
            "migration_plan": [asdict(phase) for phase in MIGRATION_PLAN],
        }

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Any, exc: Exception) -> JSONResponse:
        # Keep errors explicit while avoiding leakage of internals in production.
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "error_type": exc.__class__.__name__,
            },
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
