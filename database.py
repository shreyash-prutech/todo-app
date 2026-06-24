"""Database configuration and session management.

This module is intentionally stable and framework-agnostic so it can support the
current Flask application while enabling an incremental migration to FastAPI.

Migration strategy supported by this layer:
1. Preserve the existing database schema and behavior.
2. Upgrade dependencies (SQLAlchemy first, then drivers/alembic as needed) while
   keeping the public API in this module intact.
3. Add golden-master contract tests around current repository/service behavior.
4. Introduce a parity FastAPI API layer that uses the same session/engine.
5. Cut over routes slice-by-slice only after parity is proven.

Important constraints:
- Do not auto-migrate schema here.
- Do not introduce web-framework-specific behavior here.
- Keep session lifecycle explicit and predictable for both Flask and FastAPI.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, scoped_session, sessionmaker

try:
    # Python 3.11+ or environment variable-based config in deployment.
    DATABASE_URL = os.environ["DATABASE_URL"]
except KeyError:
    # Local default suitable for development/testing; production should provide
    # DATABASE_URL explicitly.
    DATABASE_URL = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")

# SQLAlchemy engine settings chosen to preserve existing behavior while remaining
# safe for incremental modernization.
_engine_kwargs = {
    "future": True,
    "pool_pre_ping": True,
}

# SQLite needs special handling for multithreaded access in development/tests.
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine: Engine = create_engine(DATABASE_URL, **_engine_kwargs)

# Session factory shared by Flask views, background jobs, and FastAPI dependencies.
# expire_on_commit=False helps preserve object state after commit, matching many
# legacy Flask patterns and making golden-master assertions easier during migration.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)

# Backward-compatible scoped session for legacy Flask code that expects a global
# request-bound session pattern. FastAPI should prefer get_db() below.
session_factory = scoped_session(SessionLocal)

Base = declarative_base()


def init_db() -> None:
    """Initialize database tables.

    This is intentionally conservative: it creates missing tables without altering
    existing schema. Schema evolution should be handled via migrations and verified
    against golden-master tests before route cutover.
    """

    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Return a new SQLAlchemy Session.

    Prefer this for explicit lifecycle management in services, repositories,
    scripts, and FastAPI dependencies.
    """

    return SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    Example:
        with session_scope() as session:
            ...
    """

    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def legacy_session_scope() -> Iterator[Session]:
    """Compatibility wrapper for legacy Flask code paths.

    This mirrors the current behavior of request-scoped session handling while the
    application migrates route-by-route to dependency-injected FastAPI endpoints.
    """

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        session_factory.remove()


async def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session.

    Usage:
        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    This keeps the persistence layer consistent during the parity API phase.
    """

    db = get_session()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_db",
    "get_session",
    "init_db",
    "legacy_session_scope",
    "session_factory",
    "session_scope",
]
