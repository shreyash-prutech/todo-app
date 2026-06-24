"""ORM/domain model inspection and migration planning utilities.

This module is intentionally light on framework coupling so it can be used
as part of an incremental Flask-to-FastAPI migration strategy without forcing
schema or behavior changes before parity is proven.

Migration plan embodied by this module:
1. Preserve current ORM/domain model contracts and database schema.
2. Add golden-master contract tests around existing Flask behavior.
3. Upgrade dependencies in small, verified steps.
4. Introduce a FastAPI parity layer that mirrors current endpoints.
5. Cut over routes slice-by-slice only after parity is demonstrated.

Notes:
- This file does not perform framework-specific setup.
- It exposes helpers to inventory model metadata and compare expected vs.
  actual schema state during migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ColumnSpec:
    """Framework-agnostic description of a database column."""

    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    unique: bool = False
    index: bool = False


@dataclass(frozen=True)
class RelationSpec:
    """Framework-agnostic description of a relationship between models."""

    name: str
    target_model: str
    cardinality: str  # e.g. "one-to-one", "one-to-many", "many-to-many"
    back_populates: Optional[str] = None
    nullable: bool = True


@dataclass(frozen=True)
class ModelSpec:
    """Domain model metadata used to validate ORM parity."""

    name: str
    table_name: str
    columns: Tuple[ColumnSpec, ...] = field(default_factory=tuple)
    relations: Tuple[RelationSpec, ...] = field(default_factory=tuple)
    schema: Optional[str] = None


@dataclass(frozen=True)
class SchemaDrift:
    """Represents a discrepancy between expected and observed schema."""

    model_name: str
    issue: str
    expected: Optional[Any] = None
    observed: Optional[Any] = None


@dataclass(frozen=True)
class MigrationPhase:
    """Represents a step in the migration plan."""

    name: str
    description: str
    order: int


DEFAULT_MIGRATION_PLAN: Tuple[MigrationPhase, ...] = (
    MigrationPhase(
        name="golden_master_contract_tests",
        description=(
            "Capture current Flask behavior with golden-master contract tests "
            "covering request/response payloads, status codes, validation, and "
            "side effects."
        ),
        order=1,
    ),
    MigrationPhase(
        name="dependency_upgrade",
        description=(
            "Upgrade runtime and ORM dependencies incrementally, validating the "
            "existing Flask app and database interactions at each step."
        ),
        order=2,
    ),
    MigrationPhase(
        name="fastapi_parity_layer",
        description=(
            "Introduce a FastAPI layer that mirrors the current Flask API "
            "contracts while preserving current database schema and behavior."
        ),
        order=3,
    ),
    MigrationPhase(
        name="slice_by_slice_route_cutover",
        description=(
            "Move endpoints one slice at a time from Flask to FastAPI, keeping "
            "the legacy path available until parity is verified."
        ),
        order=4,
    ),
    MigrationPhase(
        name="schema_preservation_until_parity",
        description=(
            "Preserve current database schema and ORM mappings until parity is "
            "proven and any schema migrations can be justified by tests."
        ),
        order=5,
    ),
)


def build_migration_plan() -> Tuple[MigrationPhase, ...]:
    """Return the recommended incremental Flask-to-FastAPI migration plan."""

    return DEFAULT_MIGRATION_PLAN


def inspect_model_specs(models: Iterable[ModelSpec]) -> Dict[str, Dict[str, Any]]:
    """Convert model specs into a serializable inspection payload.

    This is useful for test fixtures, contract snapshots, and migration reviews.
    """

    payload: Dict[str, Dict[str, Any]] = {}
    for model in models:
        payload[model.name] = {
            "table_name": model.table_name,
            "schema": model.schema,
            "columns": [
                {
                    "name": col.name,
                    "type": col.type,
                    "nullable": col.nullable,
                    "default": col.default,
                    "primary_key": col.primary_key,
                    "unique": col.unique,
                    "index": col.index,
                }
                for col in model.columns
            ],
            "relations": [
                {
                    "name": rel.name,
                    "target_model": rel.target_model,
                    "cardinality": rel.cardinality,
                    "back_populates": rel.back_populates,
                    "nullable": rel.nullable,
                }
                for rel in model.relations
            ],
        }
    return payload


def detect_schema_drift(
    expected: Sequence[ModelSpec],
    observed: Mapping[str, Mapping[str, Any]],
) -> List[SchemaDrift]:
    """Compare expected model specs to observed runtime metadata.

    The observed mapping can come from SQLAlchemy reflection, Alembic metadata,
    or any other schema source. The function stays intentionally generic so it
    can be used throughout the migration without coupling to a specific ORM.
    """

    drift: List[SchemaDrift] = []

    for model in expected:
        observed_model = observed.get(model.name)
        if observed_model is None:
            drift.append(
                SchemaDrift(
                    model_name=model.name,
                    issue="missing_model",
                    expected=model.table_name,
                    observed=None,
                )
            )
            continue

        observed_table_name = observed_model.get("table_name")
        if observed_table_name != model.table_name:
            drift.append(
                SchemaDrift(
                    model_name=model.name,
                    issue="table_name_mismatch",
                    expected=model.table_name,
                    observed=observed_table_name,
                )
            )

        expected_columns = {col.name: col for col in model.columns}
        observed_columns = {
            col.get("name"): col for col in observed_model.get("columns", []) if col.get("name")
        }

        for col_name, col in expected_columns.items():
            observed_col = observed_columns.get(col_name)
            if observed_col is None:
                drift.append(
                    SchemaDrift(
                        model_name=model.name,
                        issue=f"missing_column:{col_name}",
                        expected=col,
                        observed=None,
                    )
                )
                continue

            for key, expected_value in (
                ("type", col.type),
                ("nullable", col.nullable),
                ("default", col.default),
                ("primary_key", col.primary_key),
                ("unique", col.unique),
                ("index", col.index),
            ):
                observed_value = observed_col.get(key)
                if observed_value != expected_value:
                    drift.append(
                        SchemaDrift(
                            model_name=model.name,
                            issue=f"column_mismatch:{col_name}:{key}",
                            expected=expected_value,
                            observed=observed_value,
                        )
                    )

    return drift


def is_parity_ready(drift: Sequence[SchemaDrift]) -> bool:
    """Return True when no schema drift is detected."""

    return len(drift) == 0


__all__ = [
    "ColumnSpec",
    "RelationSpec",
    "ModelSpec",
    "SchemaDrift",
    "MigrationPhase",
    "DEFAULT_MIGRATION_PLAN",
    "build_migration_plan",
    "inspect_model_specs",
    "detect_schema_drift",
    "is_parity_ready",
]
