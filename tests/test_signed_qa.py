import asyncio
import base64
import json
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from test_gateway import signed, step
from test_qa import Port, Scripted, proposal, source

from vmarket_ai.app import create_app
from vmarket_ai.database import create_db_engine
from vmarket_ai.providers.openrouter import ProviderError
from vmarket_ai.qa.backend import DEMO_COLLECTIONS
from vmarket_ai.qa.fake import FakeEvidenceModel
from vmarket_ai.qa.service import AnswerService
from vmarket_ai.settings import Settings


def setup(migrated, enabled=True):
    key = Ed25519PrivateKey.generate()
    config = migrated.model_copy(
        update={
            "mode": "integrated",
            "agent_enabled": True,
            "qa_enabled": enabled,
            "gateway_public_keys": {
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        }
    )
    citation = source()
    port = Port([citation])
    qa = AnswerService(port, Scripted(proposal(citation)), mode="fake")
    client = TestClient(
        create_app(config, create_db_engine(config), qa_service=qa),
        base_url="http://127.0.0.1:8090",
    )
    return key, client, citation, port


def post(client, key, path, operation, body, **claims):
    headers, raw = signed(
        key, step(), body=json.dumps(body).encode(), path=path, operation=operation, **claims
    )
    return client.post(path, headers=headers, content=raw)


def test_signed_answer_and_source_revalidate_current_access(migrated):
    key, client, citation, port = setup(migrated)
    scope = [str(DEMO_COLLECTIONS[0])]
    with client:
        result = post(
            client,
            key,
            "/ai/ask",
            "ask",
            {
                "question": "Which encoding?",
                "language": "en",
                "collection_ids": scope,
            },
            collection_ids=scope,
        )
        assert result.status_code == 200
        assert result.json()["answer"] == "Original bytes use UTF-8."
        body = {"chunk_id": str(citation.chunk_id), "collection_ids": scope}
        opened = post(
            client, key, "/ai/citations/read", "documents_read", body, collection_ids=scope
        )
        assert opened.status_code == 200
        schema = json.loads(
            Path("docs/contracts/bff-tool-gateway.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator({**schema, "$ref": "#/$defs/CitationReadResponse"}).validate(
            opened.json()
        )
        assert opened.json()["excerpt"] == citation.text
        assert "raw_sha256" not in opened.json()
        port.revoked = True
        denied = post(
            client, key, "/ai/citations/read", "documents_read", body, collection_ids=scope
        )
        missing = post(
            client,
            key,
            "/ai/citations/read",
            "documents_read",
            {**body, "chunk_id": str(uuid4())},
            collection_ids=scope,
        )
        assert denied.status_code == missing.status_code == 404
        assert denied.json()["code"] == missing.json()["code"] == "DOCUMENT_NOT_AVAILABLE"
        assert client.get(f"/ai/citations/{citation.chunk_id}").status_code == 404


def test_signed_qa_scope_operation_and_disabled_boundary(migrated):
    key, client, citation, port = setup(migrated)
    scope = [str(DEMO_COLLECTIONS[0])]
    body = {
        "question": "Which encoding?",
        "language": "en",
        "collection_ids": [str(DEMO_COLLECTIONS[1])],
    }
    with client:
        assert client.post("/ai/ask", json=body).status_code == 401
        assert post(client, key, "/ai/ask", "ask", body, collection_ids=scope).status_code == 403
        assert post(client, key, "/ai/ask", "documents_read", body).status_code == 401
        assert (
            post(
                client,
                key,
                "/ai/citations/read",
                "documents_read",
                {
                    "chunk_id": str(citation.chunk_id),
                    "collection_ids": [str(DEMO_COLLECTIONS[1])],
                },
                collection_ids=scope,
            ).status_code
            == 403
        )
        assert (
            post(
                client, key, "/ai/ask", "ask", {**body, "collection_ids": scope}, step=1
            ).status_code
            == 403
        )
        assert port.called == 0
    key, client, _, _ = setup(migrated, enabled=False)
    with client:
        assert client.post("/ai/ask", json=body).status_code == 404
        assert client.post("/ai/citations/read", json={}).status_code == 404


def test_integrated_qa_configuration_requires_signed_gateway_and_dedicated_storage():
    key = Ed25519PrivateKey.generate()
    settings = Settings(
        _env_file=None,
        mode="integrated",
        qa_enabled=True,
        agent_enabled=True,
        database_url="postgresql+psycopg://ai_app:local@127.0.0.1/vmarket_ai_test",
        gateway_public_keys={
            "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
        },
    )
    assert settings.qa_enabled and settings.mode == "integrated"


def test_fake_qa_abstains_and_provider_failure_is_sanitized(migrated):
    key = Ed25519PrivateKey.generate()
    scope = [str(DEMO_COLLECTIONS[0])]
    # Replace the injected model, without changing the real route/security boundary.
    config = migrated.model_copy(
        update={
            "mode": "integrated",
            "agent_enabled": True,
            "qa_enabled": True,
            "gateway_public_keys": {
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        }
    )
    body = {"question": "Which encoding?", "language": "en", "collection_ids": scope}
    for model, status in [
        (FakeEvidenceModel(), 200),
        (Scripted(error=ProviderError()), 503),
    ]:
        qa = AnswerService(Port([source()]), model, mode="fake")
        with TestClient(
            create_app(config, create_db_engine(config), qa_service=qa),
            base_url="http://127.0.0.1:8090",
        ) as client:
            response = post(client, key, "/ai/ask", "ask", body, collection_ids=scope)
            assert response.status_code == status
            assert "private-upstream-detail" not in response.text
            if status == 200:
                assert response.json()["status"] == "abstained"
                assert response.json()["answer"] is None


def test_signed_qa_outer_deadline_cancels_provider_work(migrated):
    key = Ed25519PrivateKey.generate()
    stopped = []

    class Slow:
        async def complete(self, request):
            try:
                await asyncio.sleep(10)
            finally:
                stopped.append(True)

    config = migrated.model_copy(
        update={
            "mode": "integrated",
            "agent_enabled": True,
            "qa_enabled": True,
            "request_deadline_seconds": 0.1,
            "gateway_public_keys": {
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        }
    )
    qa = AnswerService(Port([source()]), Slow(), mode="fake")
    scope = [str(DEMO_COLLECTIONS[0])]
    with TestClient(
        create_app(config, create_db_engine(config), qa_service=qa),
        base_url="http://127.0.0.1:8090",
    ) as client:
        response = post(
            client,
            key,
            "/ai/ask",
            "ask",
            {"question": "Which encoding?", "language": "en", "collection_ids": scope},
            collection_ids=scope,
        )
        assert response.status_code == 504
        assert stopped == [True]
