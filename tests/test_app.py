import json
import logging
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from vmarket_ai.app import create_app


def test_health_works_without_keys_and_database(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert UUID(response.headers["x-request-id"])
        assert response.headers["cache-control"] == "no-store"
        assert settings.openrouter_api is None


def test_readiness_does_not_claim_missing_migrations_ready(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "provider_mode": "fake"}


def test_readiness_after_migration_matches_contract(migrated):
    from pathlib import Path

    schema = json.loads(
        Path("docs/contracts/bff-tool-gateway.schema.json").read_text(encoding="utf-8")
    )
    with TestClient(create_app(migrated)) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        Draft202012Validator({**schema, "$ref": "#/$defs/Readiness"}).validate(response.json())


def test_safe_request_id_round_trip(settings):
    request_id = str(uuid4())
    with TestClient(create_app(settings)) as client:
        response = client.get("/health", headers={"X-Request-ID": request_id})
        assert response.headers["x-request-id"] == request_id


def test_invalid_and_duplicate_request_ids_are_not_reflected(settings):
    with TestClient(create_app(settings)) as client:
        for headers in [
            {"X-Request-ID": "sentinel-private-token"},
            [("X-Request-ID", str(uuid4())), ("X-Request-ID", str(uuid4()))],
        ]:
            response = client.get("/health", headers=headers)
            assert response.status_code == 400
            assert "sentinel-private-token" not in response.text
            assert UUID(response.headers["x-request-id"])


def test_unknown_product_routes_are_unavailable_and_do_not_echo_inputs(settings, caplog):
    with (
        caplog.at_level(logging.INFO, logger="vmarket_ai"),
        TestClient(create_app(settings)) as client,
    ):
        response = client.post("/ai/ask?key=sentinel-secret", json={"question": "sentinel-prompt"})
        assert response.status_code == 404
        assert response.json()["code"] == "ROUTE_NOT_AVAILABLE"
        events = [json.loads(r.message) for r in caplog.records if r.name == "vmarket_ai"]
        assert events[-1]["route"] == "unknown"
        assert "sentinel-secret" not in caplog.text + response.text
        assert "sentinel-prompt" not in caplog.text + response.text


def test_oversize_request_rejected_before_routing(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/ai/ask", content=b"x" * 65537)
        assert response.status_code == 413
        assert response.json()["code"] == "INPUT_TOO_LARGE"


def test_exact_boundary_reaches_router(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/ai/ask", content=b"x" * 65536).status_code == 404


def test_unexpected_error_is_sanitized(settings, monkeypatch, caplog):
    def fail(_):
        raise RuntimeError("sentinel-database-password")

    monkeypatch.setattr("vmarket_ai.app.database_ready", fail)
    with (
        caplog.at_level(logging.INFO, logger="vmarket_ai"),
        TestClient(create_app(settings)) as client,
    ):
        response = client.get("/ready")
        assert response.status_code == 500
        assert response.json()["code"] == "INTERNAL_ERROR"
        assert "sentinel-database-password" not in response.text + caplog.text


def test_actual_openapi_has_only_implemented_paths(settings):
    with TestClient(create_app(settings)) as client:
        response = client.get("/openapi.json")
        assert set(response.json()["paths"]) == {"/health", "/ready"}
        assert client.post("/health").status_code == 405


async def test_async_health_transport(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.json() == {"status": "ok"}
