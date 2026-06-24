"""Database session management and migration helpers for FastAPI.

This module is intentionally conservative: it preserves the current database
schema and provides a compatibility layer for an incremental Flask-to-FastAPI
migration.

Migration strategy supported by this module
==========================================
1. Golden-master contract tests
   - Keep existing CRUD/query behavior stable while tests assert current API
     contracts and database side-effects.
2. Dependency upgrade
   - Centralize engine/session creation here so dependency changes only affect
     one module.
3. Parity API layer
   - FastAPI dependencies can use ``get_db`` while legacy code may still call
     ``session_scope`` or ``db_session``.
4. Slice-by-slice route cutover
   - Move routes one at a time to FastAPI dependencies without changing schema
     or transaction behavior until parity is proven.

The implementation below provides:
- A singleton SQLAlchemy engine
- A configurable session factory
- A FastAPI dependency for session injection
- Backwards-compatible context manager helpers for legacy Flask code
- Utility functions to initialize/dispose the database cleanly in tests and app
  startup/shutdown hooks

Configuration
-------------
Set ``DATABASE_URL`` in the environment. If not provided, a SQLite database is
used at ``./app.db`` to preserve local development behavior.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

try:
    # FastAPI is optional at import time for legacy environments or unit tests.
    from fastapi import Depends
except Exception:  # pragma: no cover - FastAPI may not be installed in all contexts
    Depends = None  # type: ignore[assignment]

# SQLAlchemy session configuration. Keep defaults conservative for parity with
# existing Flask-style request scoped sessions.
_SESSION_KWARGS = {
    "autocommit": False,
    "autoflush": False,
    "expire_on_commit": False,
}


def _build_database_url() -> str:
    """Resolve the database URL from environment with a safe local fallback."""

    return os.getenv("DATABASE_URL", "sqlite:///./app.db")


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create (or reuse) the SQLAlchemy engine.

    The engine is cached so the application and tests share a single lazily
    initialized connection configuration. SQLite gets special handling to allow
    thread-safe use in FastAPI/pytest environments.
    """

    database_url = _build_database_url()
    connect_args = {}
    engine_kwargs = {}

    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            # In-memory SQLite requires a static pool to preserve state across
            # connections for tests and local runs.
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, connect_args=connect_args, **engine_kwargs)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    """Return the shared session factory bound to the cached engine."""

    return sessionmaker(bind=get_engine(), **_SESSION_KWARGS)


def create_db_session() -> Session:
    """Create a new SQLAlchemy session.

    Use this for explicit transaction control in services, jobs, or legacy code
    that does not use dependency injection.
    """

    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    This preserves the familiar Flask-era pattern:

    .. code-block:: python

        with session_scope() as db:
            ...

    The session commits on success, rolls back on error, and always closes.
    """

    session = create_db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_session() -> Iterator[Session]:
    """Compatibility alias for older code paths.

    Kept intentionally for migration parity and golden-master tests.
    """

    with session_scope() as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    Example:

    .. code-block:: python

        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The session is committed on successful request completion and rolled back
    if an exception is raised, preserving current behavior during the migration.
    """

    session = create_db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(metadata=None) -> None:
    """Initialize database schema without altering existing tables.

    ``metadata`` should be a SQLAlchemy MetaData object or declarative base
    metadata. This helper intentionally only creates missing tables; it does not
    perform destructive migrations so the schema remains stable until parity is
    proven.
    """

    if metadata is None:
        return
    metadata.create_all(bind=get_engine())


def dispose_engine() -> None:
    """Dispose of the cached engine and clear factories.

    Useful in tests to ensure each case starts from a clean connection state.
    """

    engine = get_engine()
    engine.dispose()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


# Optional FastAPI dependency alias for cleaner imports in route modules.
if Depends is not None:
    DBSession = Depends(get_db)
else:  # pragma: no cover
    DBSession = None


__all__ = [
    "DBSession",
    "create_db_session",
    "db_session",
    "dispose_engine",
    "get_db",
    "get_engine",
    "get_session_factory",
    "init_db",
    "session_scope",
]
