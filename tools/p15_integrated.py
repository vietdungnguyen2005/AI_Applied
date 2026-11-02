"""Docker AI gateway + Docker storage + current host Java/Next, fake provider only."""

import argparse
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import httpx
from p11_local_smoke import main


def exercise(*, operator_login, report, snapshot, sql_connect, stop_ai, restart_ai, **unused):
    with sql_connect() as connection:
        before = snapshot(connection)
    operator, csrf = operator_login()
    with closing(operator):
        headers = {"X-CSRF-TOKEN": csrf}

        def call(body, expected=200):
            response = operator.post("/api/ops/ai/runs", json=body, headers=headers)
            assert response.status_code == expected, (body["action"], response.status_code)
            return response.json()

        created = call({"action": "start", "question": "List imports"})["run"]
        with httpx.Client(trust_env=False) as direct:
            denied = direct.post("http://127.0.0.1:8094/ai/agent/step", json={})
            assert denied.status_code == 401
            assert direct.post("http://127.0.0.1:8094/ai/ask", json={}).status_code == 404
        stop_ai()
        outage = call({"action": "inspect", "run_id": created["run_id"]}, 503)
        manual = operator.get("/api/ops/integration-profiles")
        assert manual.status_code == 200
        restart_ai()
        restored = call({"action": "inspect", "run_id": created["run_id"]})["run"]
        assert restored["status"] == "started" and restored["revision"] == 0
        completed = call({"action": "resume", "run_id": restored["run_id"], "expected_revision": 0})
        assert completed["run"]["status"] == "completed"
        assert completed["observations"][0]["data"] == {"imports": []}
        call({"action": "inspect", "run_id": str(uuid4())}, 404)
    with sql_connect() as connection:
        after = snapshot(connection)
    assert before == after
    report.update(
        status="PASS",
        business_before=before,
        business_after=after,
        business_unchanged_11_tables=True,
        unsigned_step_http=401,
        unsigned_qa_http=404,
        ai_outage_http=503,
        manual_profiles_during_ai_outage_http=200,
        outage_code=outage["code"],
        durable_restart_preserved=True,
        observed_import_count=0,
        external_provider_calls=0,
        scope=(
            "actual local Docker AI/PG plus host Java/BFF; fake planner, no semantic model quality"
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project2", type=Path, required=True)
    parser.add_argument("--image", default="vmarket-ai:p15-local")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.project2, args.output, container_image=args.image, checks=exercise)
    print("P15_INTEGRATED_PASS")
