"""Actual loopback Ollama functional smoke with explicit test-fixture retrieval.

Run from the repository root in the dev environment. This bypasses production storage
validation only through explicit test dependency injection; never launches a listener.
It does not exercise Java, PostgreSQL, E5 retrieval or held-out model quality.
"""

import base64
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path("tests").resolve()))
from conftest import migrate
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_qa import Port, source
from test_signed_qa import post

from vmarket_ai.app import create_app
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.qa.backend import DEMO_COLLECTIONS
from vmarket_ai.qa.service import AnswerService
from vmarket_ai.settings import Settings

key = Ed25519PrivateKey.generate()
config = Settings(
    _env_file=None,
    provider_mode="local",
    request_deadline_seconds=25,
    database_url=SecretStr(f"sqlite+pysqlite:///.local/p12-model-{uuid4().hex}.db"),
)
migrate(config)
config = config.model_copy(
    update={
        "mode": "integrated",
        "qa_enabled": True,
        "agent_enabled": True,
        "gateway_public_keys": {
            "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
        },
    }
)
port = Port(
    [
        source(
            "Supplier B supplies UTF-8 original bytes. "
            "Preserve the original file, declared encoding and line endings."
        )
    ]
)
qa = AnswerService(port, OllamaChatModel(config), mode="local", deadline_seconds=25)
scope = [str(DEMO_COLLECTIONS[1])]
with TestClient(create_app(config, qa_service=qa), base_url="http://127.0.0.1:8090") as client:
    r = post(
        client,
        key,
        "/ai/ask",
        "ask",
        {
            "question": "Which original byte encoding does Supplier B supply?",
            "language": "en",
            "collection_ids": scope,
        },
        collection_ids=scope,
    )
    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "actual local Ollama through signed HTTP, explicitly injected single-source "
            "retrieval fixture and SQLite nonce storage; "
            "NOT Java/PG/E5 integration or held-out quality"
        ),
        "http": r.status_code,
        "response": r.json(),
        "model": config.ollama_model,
        "external_inference_calls": 0,
    }
    Path(".local/P12-local-model.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert r.status_code == 200 and r.json()["status"] == "answered", (
        "Local model fixture did not produce supported answer"
    )
    print("LOCAL_MODEL_SIGNED_HTTP_PASS")
