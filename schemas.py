"""Request/response schemas for an incremental Flask-to-FastAPI migration plan.

This module is intentionally framework-agnostic so the same contract definitions can
be reused for:

- golden-master contract tests against the current Flask API
- a parity FastAPI layer that mirrors current behavior
- future slice-by-slice route cutover work

The plan encoded by these schemas follows a safe migration sequence:

1. Freeze current behavior with golden-master contract tests.
2. Upgrade dependencies in small, controlled steps.
3. Stand up a parity API layer that matches existing request/response contracts.
4. Cut over routes slice-by-slice only after parity is proven.
5. Preserve the existing database schema until the new stack is contractually stable.

The schemas below are designed to capture the operational metadata needed to track
that migration without coupling the representation to either Flask or FastAPI.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


class MigrationPhase(str, Enum):
    """High-level migration phases."""

    GOLDEN_MASTER = "golden_master"
    DEPENDENCY_UPGRADE = "dependency_upgrade"
    PARITY_API = "parity_api"
    ROUTE_CUTOVER = "route_cutover"
    DATABASE_FREEZE = "database_freeze"


class RouteState(str, Enum):
    """State of an individual route during the migration."""

    LEGACY_ONLY = "legacy_only"
    DUAL_RUNNING = "dual_running"
    PARITY_VALIDATED = "parity_validated"
    CUTOVER_READY = "cutover_ready"
    CUTOVER_COMPLETE = "cutover_complete"
    ROLLED_BACK = "rolled_back"


class ContractTestStatus(str, Enum):
    """Status for a golden-master contract test suite or case."""

    NOT_STARTED = "not_started"
    PASSING = "passing"
    FAILING = "failing"
    QUARANTINED = "quarantined"
    OBSOLETE = "obsolete"


class DependencyUpgradeStatus(str, Enum):
    """Status of a dependency upgrade task."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class DatabaseSchemaStatus(str, Enum):
    """Database schema posture during migration."""

    LOCKED = "locked"
    READ_ONLY_CHANGES = "read_only_changes"
    COMPATIBILITY_LAYER = "compatibility_layer"
    MIGRATION_READY = "migration_ready"
    MIGRATED = "migrated"


class APIStyle(str, Enum):
    """API surface being described or targeted."""

    FLASK = "flask"
    FASTAPI = "fastapi"
    PARITY = "parity"


class RequestEnvelope(BaseModel):
    """Generic request envelope used by migration tooling and contract tests.

    This keeps the payload generic so it can represent:

    - a captured legacy Flask request
    - a parity FastAPI request
    - a normalized contract-test fixture
    """

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"] = Field(
        ...,
        description="HTTP method for the request.",
    )
    path: str = Field(..., min_length=1, description="Normalized request path.")
    query_params: Dict[str, Any] = Field(default_factory=dict, description="Query string parameters.")
    headers: Dict[str, str] = Field(default_factory=dict, description="Relevant HTTP headers.")
    path_params: Dict[str, Any] = Field(default_factory=dict, description="Path parameters, if any.")
    body: Optional[Dict[str, Any]] = Field(default=None, description="JSON request body, if present.")
    api_style: APIStyle = Field(default=APIStyle.PARITY, description="Origin or target API style.")
    captured_at: Optional[datetime] = Field(default=None, description="Timestamp of capture, if available.")


class ResponseEnvelope(BaseModel):
    """Generic response envelope for contract comparison.

    The representation intentionally includes the fields most commonly needed for
    golden-master comparisons while staying framework-neutral.
    """

    status_code: int = Field(..., ge=100, le=599, description="HTTP status code.")
    headers: Dict[str, str] = Field(default_factory=dict, description="Relevant HTTP headers.")
    body: Optional[Any] = Field(default=None, description="Decoded response body.")
    elapsed_ms: Optional[float] = Field(default=None, ge=0, description="Observed latency in milliseconds.")
    api_style: APIStyle = Field(default=APIStyle.PARITY, description="Origin or target API style.")
    captured_at: Optional[datetime] = Field(default=None, description="Timestamp of capture, if available.")


class GoldenMasterTestCase(BaseModel):
    """A single contract test case used to freeze current behavior."""

    name: str = Field(..., min_length=1, description="Stable test case name.")
    request: RequestEnvelope
    expected_response: ResponseEnvelope
    status: ContractTestStatus = Field(default=ContractTestStatus.NOT_STARTED)
    notes: Optional[str] = Field(default=None, description="Migration notes or observed quirks.")
    allow_header_variance: List[str] = Field(
        default_factory=list,
        description="Headers allowed to differ without failing the contract.",
    )
    allow_body_variance_paths: List[str] = Field(
        default_factory=list,
        description="JSON pointer-like paths allowed to vary without failing the contract.",
    )


class DependencyUpgradeTask(BaseModel):
    """A single dependency upgrade step within the migration plan."""

    package_name: str = Field(..., min_length=1, description="Package to upgrade.")
    current_version: Optional[str] = Field(default=None, description="Currently deployed version.")
    target_version: str = Field(..., min_length=1, description="Target version after upgrade.")
    status: DependencyUpgradeStatus = Field(default=DependencyUpgradeStatus.PLANNED)
    reason: Optional[str] = Field(default=None, description="Why this upgrade is needed.")
    verification_steps: List[str] = Field(
        default_factory=list,
        description="Checks required to verify the upgrade is safe.",
    )


class RouteMigrationPlan(BaseModel):
    """Per-route migration plan for slice-by-slice cutover."""

    route_name: str = Field(..., min_length=1, description="Stable logical route name.")
    legacy_path: str = Field(..., min_length=1, description="Current Flask route path.")
    parity_path: str = Field(..., min_length=1, description="Equivalent FastAPI parity route path.")
    methods: List[Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]] = Field(
        default_factory=list,
        description="HTTP methods covered by this route.",
    )
    state: RouteState = Field(default=RouteState.LEGACY_ONLY)
    contract_test_cases: List[str] = Field(
        default_factory=list,
        description="Names of golden-master contract test cases covering this route.",
    )
    parity_checks_passed: bool = Field(default=False, description="Whether parity checks have passed.")
    rollback_plan: Optional[str] = Field(default=None, description="Rollback instructions for this route.")
    cutover_prerequisites: List[str] = Field(
        default_factory=list,
        description="Requirements that must be satisfied before cutover.",
    )


class DatabaseSchemaPlan(BaseModel):
    """Database schema preservation plan during migration."""

    status: DatabaseSchemaStatus = Field(default=DatabaseSchemaStatus.LOCKED)
    preserve_existing_schema: bool = Field(
        default=True,
        description="Whether the current schema must remain unchanged until parity is proven.",
    )
    allowed_changes: List[str] = Field(
        default_factory=list,
        description="Explicitly allowed schema changes, if any.",
    )
    migration_notes: Optional[str] = Field(default=None, description="Notes about schema compatibility.")
    schema_version: Optional[str] = Field(default=None, description="Current schema version identifier.")

    @field_validator("preserve_existing_schema")
    @classmethod
    def _must_preserve_when_locked(cls, v: bool, info: Any) -> bool:
        status = info.data.get("status")
        if status == DatabaseSchemaStatus.LOCKED and not v:
            raise ValueError("Existing schema must be preserved while schema status is 'locked'.")
        return v


class MigrationPlan(BaseModel):
    """Top-level migration plan.

    This is the canonical analysis schema for tracking an incremental Flask-to-FastAPI
    migration while preserving production behavior.
    """

    name: str = Field(..., min_length=1, description="Human-readable migration plan name.")
    description: Optional[str] = Field(default=None, description="Short summary of the plan.")
    phase: MigrationPhase = Field(default=MigrationPhase.GOLDEN_MASTER)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    target_completion_date: Optional[date] = Field(default=None)
    owner: Optional[str] = Field(default=None, description="Responsible team or individual.")
    api_style: APIStyle = Field(default=APIStyle.PARITY)
    golden_master_tests: List[GoldenMasterTestCase] = Field(default_factory=list)
    dependency_upgrades: List[DependencyUpgradeTask] = Field(default_factory=list)
    route_plans: List[RouteMigrationPlan] = Field(default_factory=list)
    database_schema: DatabaseSchemaPlan = Field(default_factory=DatabaseSchemaPlan)
    risks: List[str] = Field(default_factory=list, description="Known migration risks.")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that must be true before cutover proceeds.",
    )
    observability_notes: Optional[str] = Field(
        default=None,
        description="Logging, tracing, and metrics requirements for parity validation.",
    )
    rollback_strategy: Optional[str] = Field(
        default=None,
        description="High-level plan to reverse migration if parity is not achieved.",
    )

    @field_validator("golden_master_tests")
    @classmethod
    def _require_contract_tests_for_migration(cls, v: List[GoldenMasterTestCase], info: Any) -> List[GoldenMasterTestCase]:
        phase = info.data.get("phase")
        if phase in {
            MigrationPhase.GOLDEN_MASTER,
            MigrationPhase.DEPENDENCY_UPGRADE,
            MigrationPhase.PARITY_API,
            MigrationPhase.ROUTE_CUTOVER,
        } and not v:
            raise ValueError("At least one golden-master test case is required for the migration plan.")
        return v


class ContractComparisonResult(BaseModel):
    """Result of comparing a legacy response against a parity response."""

    test_case_name: str = Field(..., min_length=1)
    passed: bool
    legacy_response: ResponseEnvelope
    parity_response: ResponseEnvelope
    differences: List[str] = Field(default_factory=list)
    compared_at: datetime = Field(default_factory=datetime.utcnow)


class MigrationStatusReport(BaseModel):
    """Operational status view of the migration."""

    plan_name: str = Field(..., min_length=1)
    phase: MigrationPhase
    route_states: Dict[str, RouteState] = Field(default_factory=dict)
    contract_test_status: Dict[str, ContractTestStatus] = Field(default_factory=dict)
    dependency_status: Dict[str, DependencyUpgradeStatus] = Field(default_factory=dict)
    database_schema_status: DatabaseSchemaStatus = Field(default=DatabaseSchemaStatus.LOCKED)
    blockers: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "APIStyle",
    "ContractComparisonResult",
    "ContractTestStatus",
    "DatabaseSchemaPlan",
    "DatabaseSchemaStatus",
    "DependencyUpgradeStatus",
    "DependencyUpgradeTask",
    "GoldenMasterTestCase",
    "Migrationাংশ",
    "MigrationPhase",
    "MigrationPlan",
    "MigrationStatusReport",
    "RequestEnvelope",
    "ResponseEnvelope",
    "RouteMigrationPlan",
    "RouteState",
]
