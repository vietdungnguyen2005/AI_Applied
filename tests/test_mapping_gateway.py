import base64
import json

import pytest
from fastapi.testclient import TestClient
from test_gateway import signed, step

from vmarket_ai.app import create_app
from vmarket_ai.database import create_db_engine
from vmarket_ai.mapping.policy import PROFILES


def client_for(migrated):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    config = migrated.model_copy(
        update={
            "mode": "integrated",
            "agent_enabled": True,
            "mapping_enabled": True,
            "gateway_public_keys": {
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        }
    )
    return key, TestClient(
        create_app(config, create_db_engine(config)), base_url="http://127.0.0.1:8090"
    )


def payload():
    return {
        "input": {
            "raw_base64": base64.b64encode(
                b"SKU,ProductName,AvailableQuantity\nVM-002,Desk,60\n"
            ).decode(),
            "declared_encoding": "UTF-8",
            "selected_vendor_code": "RIVERBYTE",
            "profile_ids": ["supplier-b"],
            "method": "rule",
            "synthetic": True,
        },
        "profile_candidates": [PROFILES[1].model_dump()],
    }


def test_integrated_mapping_requires_signed_current_profile_snapshot(migrated):
    key, client = client_for(migrated)
    body = json.dumps(payload()).encode()
    headers, body = signed(
        key, step(), body=body, path="/ai/mapping/suggest", operation="mapping_suggest"
    )
    with client:
        assert (
            client.post(
                "/ai/mapping/suggest", content=body, headers={"Content-Type": "application/json"}
            ).status_code
            == 401
        )
        response = client.post("/ai/mapping/suggest", content=body, headers=headers)
        assert response.status_code == 200, response.text
        result = response.json()
        from vmarket_ai.gateway.wire import validate

        validate("IntegratedMappingResponse", result)
        assert result["draft"]["vendor_verification"] == "bff_profile_snapshot"
        assert result["draft"]["profile_differences"][0]["version"] == 1
        assert result["draft"]["requires_human_acceptance"] is True
        assert client.post("/ai/mapping/suggest", content=body, headers=headers).status_code == 409
        assert client.get("/ai/citations/00000000-0000-0000-0000-000000000000").status_code == 404


@pytest.mark.parametrize(
    "change",
    [
        {"active": False},
        {"vendor_code": "NAMI"},
        {"encoding": "CP932"},
        {"version": 0},
        {"profile_id": "../admin"},
        {"mapping": {"sku": "SKU", "name": "SKU", "on_hand": "Q"}},
    ],
)
def test_mapping_snapshot_must_match_active_java_reference(migrated, change):
    key, client = client_for(migrated)
    data = payload()
    data["profile_candidates"][0].update(change)
    headers, body = signed(
        key,
        step(),
        body=json.dumps(data).encode(),
        path="/ai/mapping/suggest",
        operation="mapping_suggest",
    )
    with client:
        assert client.post("/ai/mapping/suggest", content=body, headers=headers).status_code == 400


def test_mapping_binds_raw_bytes_encoding_scope_and_operation(migrated):
    from vmarket_ai.qa.backend import DEMO_COLLECTIONS

    key, client = client_for(migrated)
    with client:
        for updates, expected in [
            ({"collection_ids": [str(DEMO_COLLECTIONS[0])]}, 403),
            ({"operation": "agent_step"}, 401),
            ({"step": 1}, 403),
        ]:
            headers, body = (
                signed(
                    key,
                    step(),
                    body=json.dumps(payload()).encode(),
                    path="/ai/mapping/suggest",
                    operation="mapping_suggest",
                    **updates,
                )
                if "operation" not in updates
                else signed(
                    key,
                    step(),
                    body=json.dumps(payload()).encode(),
                    path="/ai/mapping/suggest",
                    **updates,
                )
            )
            assert (
                client.post("/ai/mapping/suggest", content=body, headers=headers).status_code
                == expected
            )
        headers, body = signed(
            key,
            step(),
            body=json.dumps(payload()).encode(),
            path="/ai/mapping/suggest",
            operation="mapping_suggest",
        )
        assert (
            client.post(
                "/ai/mapping/suggest", content=body.replace(b"UTF-8", b"CP932"), headers=headers
            ).status_code
            == 401
        )
