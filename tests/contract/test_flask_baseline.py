"""Golden-master contract tests for the current Flask API.

These tests capture the current behavior of the Flask application before any
FastAPI migration work begins. They are intentionally written to exercise the
existing Flask layer directly so that the team can preserve behavior while
upgrading dependencies, introducing a parity API layer, and cutting routes over
slice-by-slice only after parity is proven.

Keep these tests stable and update them only when the intended public contract
changes.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

import pytest


@pytest.fixture(scope="module")
def flask_client() -> Any:
    """Return a Flask test client for the current application.

    The fixture attempts a small set of common app factory/module patterns so
    the contract tests remain useful across incremental refactors.
    """

    candidates: Iterable[tuple[str, str]] = (
        ("app", "create_app"),
        ("src.app", "create_app"),
        ("api.app", "create_app"),
        ("wsgi", "app"),
        ("app", "app"),
        ("src.app", "app"),
        ("api.app", "app"),
    )

    last_error: Exception | None = None
    for module_name, attr_name in candidates:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            attr = getattr(module, attr_name)
            app = attr() if callable(attr) else attr
            if hasattr(app, "test_client"):
                return app.test_client()
        except Exception as exc:  # pragma: no cover - best-effort bootstrap
            last_error = exc
            continue

    pytest.fail(
        "Unable to locate a Flask application for contract testing. "
        "Ensure the current Flask app exposes either `create_app()` or `app` "
        "from one of: app, src.app, api.app, wsgi.",
    )
    if last_error:
        raise last_error


@pytest.fixture
def app_context(flask_client: Any) -> Any:
    """Provide an application context when the current app supports it."""

    app = flask_client.application
    if hasattr(app, "app_context"):
        with app.app_context():
            yield app
    else:
        yield app


@pytest.fixture
def _json_headers() -> dict[str, str]:
    return {"Accept": "application/json"}


@pytest.mark.contract
def test_root_or_health_endpoint_returns_success(flask_client: Any, _json_headers: dict[str, str]) -> None:
    """Capture the current top-level liveness-style behavior.

    If the application exposes a root or health endpoint, it should return a
    successful response. This is a baseline contract that should remain true
    throughout the migration.
    """

    candidate_paths = ("/", "/health", "/healthz", "/api/health")
    last_response = None
    for path in candidate_paths:
        response = flask_client.get(path, headers=_json_headers)
        last_response = response
        if response.status_code < 500:
            assert response.status_code in (200, 204)
            if response.status_code == 200 and response.data:
                content_type = response.headers.get("Content-Type", "")
                assert "json" in content_type.lower() or "text" in content_type.lower()
            return

    assert last_response is not None
    pytest.fail(
        "No baseline success response found for root/health endpoints. "
        f"Last observed status: {last_response.status_code}"
    )


@pytest.mark.contract
def test_unknown_route_still_returns_404(flask_client: Any) -> None:
    """The existing API should continue to reject unknown routes consistently."""

    response = flask_client.get("/__definitely_not_a_real_route__")
    assert response.status_code == 404


@pytest.mark.contract
def test_invalid_method_returns_expected_client_error(flask_client: Any) -> None:
    """Capture method handling on a known stable endpoint.

    This guards against accidental behavior changes during dependency upgrades or
    route proxying.
    """

    probe_paths = ("/", "/health", "/healthz", "/api/health")
    for path in probe_paths:
        get_response = flask_client.get(path)
        if get_response.status_code < 500 and get_response.status_code != 404:
            post_response = flask_client.post(path)
            assert post_response.status_code in (405, 404)
            return

    pytest.skip("No stable endpoint discovered for method-contract capture.")


@pytest.mark.contract
def test_json_error_payload_shape_is_stable_for_not_found(flask_client: Any) -> None:
    """If the API emits JSON errors, keep the shape stable during migration.

    We do not force all Flask errors to be JSON, but when JSON is returned it
    should remain parseable and include the current contract fields.
    """

    response = flask_client.get("/__definitely_not_a_real_route__")
    content_type = response.headers.get("Content-Type", "")

    if "json" not in content_type.lower():
        pytest.skip("Current Flask app does not return JSON for 404 responses.")

    payload = json.loads(response.data.decode("utf-8"))
    assert isinstance(payload, dict)
    assert payload, "Expected a non-empty JSON error payload"

    known_keys = {"error", "message", "detail", "details", "status", "code"}
    assert any(key in payload for key in known_keys), (
        "Expected one of the conventional error keys in JSON error payload; "
        f"got keys: {sorted(payload.keys())}"
    )


@pytest.mark.contract
def test_response_headers_do_not_regress_on_baseline_endpoint(flask_client: Any) -> None:
    """Baseline header assertions to detect accidental framework regressions."""

    for path in ("/", "/health", "/healthz", "/api/health"):
        response = flask_client.get(path)
        if response.status_code < 500 and response.status_code != 404:
            assert "Server" not in response.headers or response.headers["Server"]
            assert response.headers.get("Content-Type") is not None
            return

    pytest.skip("No stable endpoint discovered for header baseline capture.")


@pytest.mark.contract
def test_api_rejects_invalid_json_payload_with_client_error(flask_client: Any) -> None:
    """Capture current request validation behavior for malformed JSON bodies.

    This is useful when introducing a FastAPI parity layer because request body
    parsing and validation semantics can differ subtly between frameworks.
    """

    probe_paths = ("/", "/health", "/healthz", "/api/health")
    for path in probe_paths:
        get_response = flask_client.get(path)
        if get_response.status_code < 500 and get_response.status_code != 404:
            response = flask_client.post(
                path,
                data="{not valid json",
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code in (400, 404, 405, 415)
            return

    pytest.skip("No stable endpoint discovered for invalid JSON contract capture.")
