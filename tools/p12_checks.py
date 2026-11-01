"""P12 real Java/BFF/Python integration; all storage and keys owned by the smoke runner."""

import json
import subprocess
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg

from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS


def exercise(
    *, operator_login, sql_connect, snapshot, report, base, ai_port, provider, project2, **unused
):
    def business():
        with sql_connect() as connection:
            return snapshot(connection)

    before = business()
    operator, csrf = operator_login()
    with closing(operator):
        headers = {"X-CSRF-TOKEN": csrf}

        def call(path, body, expected=200):
            response = operator.post("/api/ops/ai/" + path, json=body, headers=headers)
            assert response.status_code == expected, (path, response.status_code)
            report["checks"].append(
                {
                    "path": path,
                    "http": response.status_code,
                    "request_id": response.headers.get("x-request-id"),
                    "response": response.json(),
                }
            )
            return response.json()

        created = call("runs", {"action": "start", "question": "List imports"})["run"]
        completed = call(
            "runs", {"action": "resume", "run_id": created["run_id"], "expected_revision": 0}
        )
        assert completed["run"]["status"] == "completed"
        assert completed["observations"][0]["data"] == {"imports": []}
        inspected = call("runs", {"action": "inspect", "run_id": created["run_id"]})
        assert inspected["observations"] == []
        assert len(inspected["run"]["observations"]) == 1
        profiles = operator.get("/api/ops/integration-profiles").json()
        profile = next(p for p in profiles if p["vendorCode"] == "RIVERBYTE" and p["active"])
        reference = {"profile_id": profile["profileId"], "profile_version": profile["version"]}
        question = {
            **reference,
            "question": "Which original byte encoding does Supplier B supply?",
            "language": "en",
        }
        abstain = call("ask", question)
        assert abstain["status"] == "abstained" and abstain["provider_mode"] == "fake"
        provider("local")
        answer = call("ask", question)
        assert answer["status"] == "answered", (
            "Local model did not establish the expected source; no quality claim"
        )
        assert "UTF-8" in answer["answer"] and answer["provider_mode"] == "local"
        source = call(
            "citations/read", {**reference, "chunk_id": answer["citations"][0]["chunk_id"]}
        )
        assert answer["answer"] in source["excerpt"]
        assert "source_url" not in source["citation"]
        call("ask", {**question, "collection_ids": [str(DEMO_COLLECTIONS[0])]}, 400)
        source_reference = {**reference, "chunk_id": source["citation"]["chunk_id"]}
        # Browser receives only its actual authenticated session cookie through stdin.
        args = {
            "base": base,
            "cookies": [
                {"name": c.name, "value": c.value, "url": base, "httpOnly": True}
                for c in operator.cookies.jar
            ],
            "profile": reference,
            "out": str(Path(__file__).resolve().parents[1] / ".local/p12-real-browser"),
        }
        browser = subprocess.run(
            ["python", "tools/qa_copilot_real.py"],
            cwd=project2,
            input=json.dumps(args),
            capture_output=True,
            text=True,
            check=False,
        )
        assert browser.returncode == 0, (
            "Actual browser smoke failed; private output is not copied to public evidence"
        )
        report["browser"] = json.loads(browser.stdout)
        # Revocation is limited to the fresh disposable AI corpus, never the default database.
        with psycopg.connect(
            host="127.0.0.1",
            port=ai_port,
            dbname="vmarket_ai_test",
            user="ai_owner",
            password="local-ai-owner-only",
        ) as connection:
            connection.execute(
                "DELETE FROM ai.collection_grants WHERE actor_id=%s AND collection_id=%s",
                (DEMO_ACTOR.id, DEMO_COLLECTIONS[1]),
            )
        revoked = call("citations/read", source_reference, 404)
        missing = call("citations/read", {**reference, "chunk_id": str(uuid4())}, 404)
        assert revoked == missing == {"code": "DOCUMENT_NOT_AVAILABLE"}
    after = business()
    assert before == after, "Read-only Copilot changed business data"
    report.update(
        status="PASS",
        timestamp_utc=datetime.now(UTC).isoformat(),
        business_before=before,
        business_after=after,
        business_unchanged_11_tables=True,
        external_provider_calls=0,
        planner="fake for durable read trace; local Qwen for grounded QA",
        model="qwen3.5:4b-q4_K_M",
        embeddings="pinned multilingual-e5-small CPU",
        scope="synthetic functional acceptance only, not held-out quality evaluation",
    )
