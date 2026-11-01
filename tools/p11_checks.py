"""Actual process restart and authorization drills against owned disposable storage."""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, suppress
from uuid import UUID

import httpx
import psycopg


def exercise(
    *,
    operator_login,
    sql_connect,
    snapshot,
    report,
    base,
    proxy,
    ai_port,
    migration_env,
    username,
    restart_ai,
    restart_bff,
):
    def ai_sql():
        return psycopg.connect(
            host="127.0.0.1",
            port=ai_port,
            dbname="vmarket_ai_test",
            user="ai_owner",
            password="local-ai-owner-only",
        )

    def business():
        with sql_connect() as c:
            return snapshot(c)

    before = business()
    operator, csrf = operator_login()
    with closing(operator):

        def call(action, expected=200, **fields):
            response = operator.post(
                "/api/ops/ai/runs",
                json={"action": action, **fields},
                headers={"X-CSRF-TOKEN": csrf},
            )
            assert response.status_code == expected, (action, response.status_code)
            data = response.json()
            report["checks"].append(
                {
                    "action": action,
                    "expected_http": expected,
                    "actual_http": response.status_code,
                    "response": data,
                    "request_id": response.headers.get("x-request-id"),
                }
            )
            return data.get("run")

        normal = call("start", question="List imports")
        done = call("resume", run_id=normal["run_id"], expected_revision=0)
        assert done["status"] == "completed" and done["step"] == 1
        count = proxy.import_reads
        call("resume", 409, run_id=normal["run_id"], expected_revision=0)
        assert proxy.import_reads == count
        timeout_run = call("start", question="List imports")
        proxy.hold = True
        began = time.monotonic()
        call("resume", 504, run_id=timeout_run["run_id"], expected_revision=0)
        elapsed = time.monotonic() - began
        assert 24 <= elapsed < 30 and proxy.import_reads == count + 1
        proxy.hold = False
        proxy.release.set()
        with ai_sql() as c:
            lease_end = c.execute(
                "SELECT lease_until FROM ai.agent_runs WHERE id=%s", (timeout_run["run_id"],)
            ).fetchone()[0]
        while int(time.time()) < lease_end:
            time.sleep(0.2)
        timed = call("inspect", run_id=timeout_run["run_id"])
        assert timed["reason"] == "OUTCOME_UNKNOWN"
        settled = call("resume", run_id=timed["run_id"], expected_revision=timed["revision"])
        assert settled["outcome"]["status"] == "abstained" and proxy.import_reads == count + 1
        report["real_deadline"] = {
            "http": 504,
            "elapsed_seconds": round(elapsed, 2),
            "no_read_redispatch": True,
        }
        count = proxy.import_reads
        interrupted = call("start", question="List imports")
        proxy.received.clear()
        proxy.release.clear()
        proxy.hold = True
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                lambda: operator.post(
                    "/api/ops/ai/runs",
                    json={
                        "action": "resume",
                        "run_id": interrupted["run_id"],
                        "expected_revision": 0,
                    },
                    headers={"X-CSRF-TOKEN": csrf},
                )
            )
            assert proxy.received.wait(15), "Expected real Java read was not dispatched"
            assert proxy.import_reads == count + 1
            with ai_sql() as c:
                checkpoint = c.execute(
                    "SELECT revision,phase,lease_until FROM ai.agent_runs WHERE id=%s",
                    (interrupted["run_id"],),
                ).fetchone()
            assert checkpoint[1] == "executing"
            bff = restart_bff()
            ai = restart_ai()
            proxy.hold = False
            proxy.release.set()
            with suppress(httpx.HTTPError):
                future.result(timeout=10)
        from p11_local_smoke import wait_http

        wait_http("http://127.0.0.1:8094/ready", ai)
        wait_http(base + "/ops", bff)
        until = time.monotonic() + 35
        while int(time.time()) < checkpoint[2] and time.monotonic() < until:
            time.sleep(0.2)
        paused = call("inspect", run_id=interrupted["run_id"])
        assert paused["status"] == "waiting_for_operator" and paused["reason"] == "OUTCOME_UNKNOWN"
        resumed = call("resume", run_id=paused["run_id"], expected_revision=paused["revision"])
        assert resumed["status"] == "completed" and resumed["outcome"]["status"] == "abstained"
        assert resumed["observations"][0]["status"] == "unavailable"
        assert proxy.import_reads == count + 1, "Interrupted GET was redispatched"
        report["process_restart"] = {
            "bff_and_python_restarted": True,
            "checkpoint_before_kill": list(checkpoint),
            "unknown_outcome_explicit": True,
            "no_read_redispatch": True,
            "observed_import_gets": proxy.import_reads,
        }
        expiry = call("start", question="List imports")
        with sql_connect() as c:
            c.execute(
                "UPDATE spring_session SET expiry_time=1,last_access_time=1 "
                "WHERE principal_name=%s",
                (username,),
            )
        call("resume", 401, run_id=expiry["run_id"], expected_revision=0)
        with ai_sql() as c:
            assert (
                c.execute(
                    "SELECT revision FROM ai.agent_runs WHERE id=%s", (expiry["run_id"],)
                ).fetchone()[0]
                == 0
            )
        renewed, csrf2 = operator_login()
        operator.cookies.update(renewed.cookies)
        csrf = csrf2
        renewed.close()
        with sql_connect() as c:
            c.execute("UPDATE auth_account SET role='VIEWER' WHERE username=%s", (username,))
        call("inspect", 403, run_id=expiry["run_id"])
        with sql_connect() as c:
            c.execute("UPDATE auth_account SET role='OPERATOR' WHERE username=%s", (username,))
        call("cancel", run_id=expiry["run_id"], expected_revision=0)
        handoff = call("start", question="Confirm import")
        waiting = call("resume", run_id=handoff["run_id"], expected_revision=0)
        assert waiting["reason"] == "BUSINESS_HANDOFF" and not waiting["can_resume"]
        call(
            "resume",
            400,
            run_id=handoff["run_id"],
            expected_revision=waiting["revision"],
            approved=True,
        )
        call("resume", 409, run_id=handoff["run_id"], expected_revision=waiting["revision"])
        call("cancel", run_id=handoff["run_id"], expected_revision=waiting["revision"])
        quota = [call("start", question="List imports")["run_id"] for _ in range(8)]
        call("start", 429, question="List imports")
        with ai_sql() as c:
            privileges = c.execute(
                "SELECT has_column_privilege('ai_app','ai.agent_runs','actor_ref','UPDATE'),"
                "has_table_privilege('ai_app','ai.agent_runs','DELETE'),"
                "has_table_privilege('ai_app','ai.agent_run_events','UPDATE')"
            ).fetchone()
            assert privileges == (False, False, False)
            traces = c.execute(
                "SELECT run_id,revision,kind,status,phase,step FROM ai.agent_run_events "
                "ORDER BY at,run_id,revision"
            ).fetchall()
            c.execute(
                "UPDATE ai.agent_runs SET expires_at=%s WHERE id=ANY(%s)",
                (int(time.time()) - 1, [UUID(s) for s in quota]),
            )
        maintenance = subprocess.run(
            [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "runs-maintain"],
            env=migration_env,
            capture_output=True,
            text=True,
            check=True,
        )
        first = json.loads(maintenance.stdout.strip().splitlines()[-1])
        assert first["expired"] == 8 and first["purged"] == 0
        with ai_sql() as c:
            assert (
                c.execute(
                    "SELECT count(*) FROM ai.agent_runs WHERE id=ANY(%s) "
                    "AND question='' AND history::jsonb='[]'::jsonb",
                    ([UUID(s) for s in quota],),
                ).fetchone()[0]
                == 8
            )
            c.execute(
                "UPDATE ai.agent_runs SET purge_after=%s WHERE id=ANY(%s)",
                (int(time.time()) - 1, [UUID(s) for s in quota]),
            )
        maintenance = subprocess.run(
            [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "runs-maintain"],
            env=migration_env,
            capture_output=True,
            text=True,
            check=True,
        )
        second = json.loads(maintenance.stdout.strip().splitlines()[-1])
        assert second["purged"] == 8
        report["retention"] = {
            "controlled_disposable_timestamps": True,
            "expire": first,
            "purge": second,
            "protected_owner_fields": list(privileges),
        }
        check_env = {
            **migration_env,
            "AI_TEST_DATABASE_URL": migration_env["AI_DATABASE_URL"],
            "AI_TEST_OWNER_DATABASE_URL": migration_env["AI_MIGRATION_DATABASE_URL"],
        }
        pg_test = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/test_runs.py", "-m", "postgres"],
            env=check_env,
            capture_output=True,
            text=True,
        )
        assert pg_test.returncode == 0, "Disposable PG CAS/permissions test failed"
        report["postgres_cas_test"] = {
            "passed": True,
            "summary": pg_test.stdout.strip().splitlines()[-1],
        }
        report["transitions"] = [
            [str(v) if isinstance(v, UUID) else v for v in row] for row in traces
        ]
    after = business()
    assert before == after, "Read-only durable run changed business data"
    report.update(
        status="PASS",
        business_before=before,
        business_after=after,
        business_unchanged_11_tables=True,
        external_provider_calls=0,
        keys="ephemeral_process_only",
        planner="fake",
        ai_storage="fresh_disposable_AI_database",
    )
