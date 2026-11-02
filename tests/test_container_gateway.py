import base64

import pytest
from pydantic import ValidationError

from vmarket_ai.settings import Settings


def config(**changes):
    values = dict(
        _env_file=None,
        mode="integrated",
        private_container=True,
        signed_container=True,
        bind_host="0.0.0.0",
        agent_enabled=True,
        gateway_public_keys={"fixture": base64.b64encode(b"x" * 32).decode()},
    )
    return values | changes


def test_signed_fake_container_is_an_explicit_integrated_mode():
    settings = Settings(**config())
    assert settings.mode == "integrated" and settings.provider_mode == "fake"
    assert settings.signed_container and not settings.qa_enabled


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "standalone"},
        {"private_container": False},
        {"bind_host": "127.0.0.1"},
        {"provider_mode": "local"},
        {"qa_enabled": True},
        {"mapping_enabled": True},
        {"qa_embedding_mode": "local"},
        {"gateway_public_keys": {}},
        {"agent_enabled": False},
    ],
)
def test_container_opt_in_cannot_expand_other_runtime_modes(changes):
    with pytest.raises(ValidationError):
        Settings(**config(**changes))


def test_signed_container_has_no_unsigned_business_route_bypass(migrated):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from fastapi.testclient import TestClient
    from test_gateway import signed, step

    from vmarket_ai.app import create_app

    key = Ed25519PrivateKey.generate()
    settings = Settings(
        **config(
            database_url=migrated.database_url,
            gateway_public_keys={
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        )
    )
    with TestClient(create_app(settings)) as client:
        for path in ("/ai/ask", "/ai/mapping/suggest", "/ai/agent/demo"):
            assert client.post(path, json={}).status_code == 404
        payload = step()
        assert client.post("/ai/agent/step", json=payload).status_code == 401
        headers, body = signed(key, payload)
        result = client.post("/ai/agent/step", content=body, headers=headers)
        assert result.status_code == 200
        assert result.json()["intent"]["tool_name"] == "get_imports"
