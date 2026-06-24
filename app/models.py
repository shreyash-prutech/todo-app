"""SQLAlchemy ORM models for the application.

This module is written to be compatible with SQLAlchemy 2.x while preserving
existing database schema behavior during the incremental Flask-to-FastAPI
migration.

Migration strategy support:
- Keep the ORM layer stable so golden-master contract tests can validate
  behavior before and after introducing the parity API layer.
- Avoid schema-changing surprises by explicitly preserving table/column names
  and legacy defaults.
- Use SQLAlchemy 2.x typed declarative mappings where practical, while
  remaining compatible with existing Flask application code and future FastAPI
  endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

# The shared Flask-SQLAlchemy extension instance used by the existing app.
# Keeping this centralized helps preserve current behavior during the gradual
# migration to FastAPI, where the same database schema and entity semantics
# should continue to apply until parity is proven.
db = SQLAlchemy()


class TimestampMixin:
    """Mixin providing created/updated timestamps with stable defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(db.Model, TimestampMixin):
    """User entity.

    Table and column names are intentionally explicit to preserve legacy schema
    during phased route cutover and contract-test validation.
    """

    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="1")
    is_admin: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="0")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} username={self.username!r}>"


class MigrationCheckpoint(db.Model):
    """Tracks application migration progress and parity checkpoints.

    This model is useful for incremental migration workflows where golden-master
    tests and cutover milestones need to be recorded without changing existing
    business tables.
    """

    __tablename__ = "migration_checkpoints"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", server_default="pending")
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<MigrationCheckpoint id={self.id!r} name={self.name!r} status={self.status!r}>"


class ContractTestSnapshot(db.Model):
    """Stores golden-master snapshot metadata for contract tests.

    The actual payload may be stored externally depending on the test harness;
    this model records snapshot identifiers and lifecycle state while preserving
    the production schema footprint.
    """

    __tablename__ = "contract_test_snapshots"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    snapshot_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ContractTestSnapshot id={self.id!r} scenario={self.scenario!r}>"


__all__ = [
    "db",
    "User",
    "MigrationCheckpoint",
    "ContractTestSnapshot",
    "TimestampMixin",
]
