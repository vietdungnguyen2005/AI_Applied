"""Opt-in disposable Java/Next/Python auth/read smoke. No deployment or persistent key setup.

Requires prepared Project2 production build/JAR, Docker, local AI PG/corpus and the AI uv env.
Private process logs stay under ignored .local; public report contains only curated evidence.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
JOB = "11111111-1111-4111-8111-111111111111"


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def wait_http(url, process):
    until = time.monotonic() + 60
    while time.monotonic() < until:
        if process.poll() is not None:
            raise RuntimeError("Owned QA service exited; inspect ignored private logs")
        try:
            if httpx.get(url, timeout=1, trust_env=False).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError("Owned QA service readiness deadline")


def main(project2: Path, output: Path):
    if output.exists():
        raise ValueError("A fresh evidence filename is required")
    project2 = project2.resolve()
    for port in (18092, 13009, 8092):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("Reserved QA port is already occupied")
    temporary = ROOT / ".local" / ("p09-smoke-" + uuid4().hex[:8])
    temporary.mkdir(parents=True)
    pg = "vmarket-p09-pg-" + uuid4().hex[:8]
    redis = "vmarket-p09-redis-" + uuid4().hex[:8]
    containers, processes, files = [], [], []
    report = {"mode": "disposable_local_integration", "external_provider_calls": 0, "checks": []}
    report["next_build_id"] = (project2 / ".next/BUILD_ID").read_text(encoding="utf-8").strip()
    report["java_jar_sha256"] = hashlib.sha256(
        (project2 / "backend/target/v-market-backend-0.1.0-SNAPSHOT.jar").read_bytes()
    ).hexdigest()
    private_key = Ed25519PrivateKey.generate()
    private_der = base64.b64encode(
        private_key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    ).decode()
    public_raw = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
    bff_secret, ops_secret, actor_key, password = (secrets.token_urlsafe(32) for _ in range(4))
    username = "p09-operator@example.test"
    password_hash = (
        command(
            [
                "python",
                "-c",
                "import sys,bcrypt;"
                "print(bcrypt.hashpw(sys.stdin.buffer.read(),bcrypt.gensalt()).decode())",
            ],
            input=password.encode(),
        )
        .decode()
        .strip()
    )
    base_env = dict(os.environ)

    def start(name, args, env, cwd):
        log = (temporary / (name + ".log")).open("wb")
        files.append(log)
        process = subprocess.Popen(
            args,
            env=env,
            cwd=cwd,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        processes.append(process)
        return process

    def sql_connect():
        return psycopg.connect(
            host="127.0.0.1",
            port=pg_port,
            dbname="vmarket",
            user="vmarket",
            password="p09-disposable-db-only",
        )

    def snapshot(connection):
        result = {}
        for table in (
            "product",
            "inventory_stock",
            "inventory_movement",
            "customer_order",
            "migration_job",
            "import_work_item",
            "staged_import_row",
            "reconciliation_run",
            "reconciliation_discrepancy",
            "integration_profile",
            "audit_event",
        ):
            result[table] = connection.execute(
                "SELECT count(*),md5(coalesce(string_agg(to_jsonb(t)::text, "
                f"E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM {table} t"
            ).fetchone()
        return result

    try:
        command(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                pg,
                "-e",
                "POSTGRES_DB=vmarket",
                "-e",
                "POSTGRES_USER=vmarket",
                "-e",
                "POSTGRES_PASSWORD=p09-disposable-db-only",
                "-p",
                "127.0.0.1::5432",
                "postgres:17.6-alpine",
            ]
        )
        containers.append(pg)
        command(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                redis,
                "-p",
                "127.0.0.1::6379",
                "redis:8.2-alpine",
            ]
        )
        containers.append(redis)
        pg_port = command(["docker", "port", pg, "5432"]).decode().strip().rsplit(":", 1)[1]
        redis_port = command(["docker", "port", redis, "6379"]).decode().strip().rsplit(":", 1)[1]
        java_env = {
            **base_env,
            "SPRING_DATASOURCE_URL": f"jdbc:postgresql://127.0.0.1:{pg_port}/vmarket",
            "SPRING_DATASOURCE_USERNAME": "vmarket",
            "SPRING_DATASOURCE_PASSWORD": "p09-disposable-db-only",
            "SPRING_DATA_REDIS_URL": f"redis://127.0.0.1:{redis_port}",
            "BFF_SHARED_SECRET": bff_secret,
            "VMARKET_OPS_SECRET": ops_secret,
            "AUTH_BOOTSTRAP_USERNAME": username,
            "AUTH_BOOTSTRAP_PASSWORD_HASH": password_hash,
            "AUTH_SECURE_COOKIE": "false",
            "IMPORT_WORKER_ENABLED": "false",
        }
        java = start(
            "java",
            [
                "java",
                "-jar",
                "backend/target/v-market-backend-0.1.0-SNAPSHOT.jar",
                "--server.port=18092",
            ],
            java_env,
            project2,
        )
        wait_http("http://127.0.0.1:18092/actuator/health", java)
        with sql_connect() as c:
            c.execute(
                "INSERT INTO migration_job(id,source_name,file_checksum,encoding,status,"
                "total_rows,rejected_rows,import_mode) "
                "VALUES(%s,'private-source.csv',%s,'UTF-8','FAILED',1,1,'METADATA_ONLY')",
                (JOB, hashlib.sha256(b"P09 fixture only").hexdigest()),
            )
            c.execute(
                "INSERT INTO import_work_item(job_id,state,last_recovery_reason) "
                "VALUES(%s,'FAILED','PRIVATE_RECOVERY_SENTINEL')",
                (JOB,),
            )
            c.execute(
                "INSERT INTO staged_import_row(job_id,row_number,external_sku,"
                "valid,validation_error) "
                "VALUES(%s,2,'PRIVATE_RAW_SKU',false,'PRIVATE_ROW_SENTINEL')",
                (JOB,),
            )
            c.execute(
                "INSERT INTO reconciliation_run(id,migration_job_id,status,mismatch_count) "
                "VALUES(%s,%s,'COMPLETED',1)",
                (str(uuid4()), JOB),
            )
            before = snapshot(c)
        ai_env = {
            **base_env,
            "AI_MODE": "integrated",
            "AI_AGENT_ENABLED": "true",
            "AI_QA_ENABLED": "false",
            "AI_MAPPING_ENABLED": "false",
            "AI_PROVIDER_MODE": "fake",
            "AI_LIVE_ENABLED": "false",
            "AI_PORT": "8092",
            "AI_BIND_HOST": "127.0.0.1",
            "AI_PRIVATE_CONTAINER": "false",
            "AI_REQUEST_DEADLINE_SECONDS": "25",
            "AI_DATABASE_URL": "postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai",
            "AI_QA_EMBEDDING_MODE": "local",
            "AI_QA_MODEL_BUNDLE": str(ROOT / ".local/models/multilingual-e5-small"),
            "AI_GATEWAY_PUBLIC_KEYS": json.dumps({"p09-ephemeral": public_raw}),
        }
        for secret_name in (
            "BFF_SHARED_SECRET",
            "VMARKET_OPS_SECRET",
            "AI_SIGNING_KEY_PKCS8_BASE64",
            "AI_ACTOR_HMAC_KEY",
        ):
            ai_env.pop(secret_name, None)
        report["no_java_or_signing_secrets_in_python_env"] = all(
            k not in ai_env
            for k in (
                "BFF_SHARED_SECRET",
                "VMARKET_OPS_SECRET",
                "AI_SIGNING_KEY_PKCS8_BASE64",
                "AI_ACTOR_HMAC_KEY",
            )
        )
        migration_env = {
            **ai_env,
            "AI_MIGRATION_DATABASE_URL": "postgresql+psycopg://ai_owner:local-ai-owner-only@127.0.0.1:5434/vmarket_ai",
        }
        command(
            [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "migrate"],
            env=migration_env,
            cwd=ROOT,
        )
        ai = start(
            "ai",
            [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "serve"],
            ai_env,
            ROOT,
        )
        wait_http("http://127.0.0.1:8092/ready", ai)
        bff_env = {
            **base_env,
            "BACKEND_ORIGIN": "http://127.0.0.1:18092",
            "BFF_SHARED_SECRET": bff_secret,
            "VMARKET_OPS_SECRET": ops_secret,
            "AI_COPILOT_ENABLED": "true",
            "AI_SERVICE_ORIGIN": "http://127.0.0.1:8092",
            "AI_SIGNING_KID": "p09-ephemeral",
            "AI_SIGNING_KEY_PKCS8_BASE64": private_der,
            "AI_ACTOR_HMAC_KEY": actor_key,
        }
        bff = start(
            "bff",
            [
                "node",
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "13009",
            ],
            bff_env,
            project2,
        )
        base = "http://127.0.0.1:13009"
        wait_http(base + "/ops", bff)
        print("DISPOSABLE_SERVICES_READY", flush=True)

        def login():
            client = httpx.Client(
                base_url=base, timeout=30, trust_env=False, headers={"Origin": base}
            )
            csrf = client.get("/api/auth/session").json()["csrfToken"]
            response = client.post(
                "/api/auth/login",
                data={"username": username, "password": password},
                headers={"X-CSRF-TOKEN": csrf},
            )
            assert response.status_code == 204, "Disposable OPERATOR login failed"
            return client, client.get("/api/auth/session").json()["csrfToken"]

        def ask(client, csrf, question, expected=200, **extra):
            response = client.post(
                "/api/ops/ai/agent",
                json={"question": question, **extra},
                headers={"X-CSRF-TOKEN": csrf},
            )
            report["checks"].append(
                {
                    "question": question,
                    "expected_http": expected,
                    "actual_http": response.status_code,
                    "request_id": response.headers.get("x-request-id"),
                    "response": response.json(),
                }
            )
            assert response.status_code == expected, "Unexpected agent HTTP result"
            assert "PRIVATE_" not in response.text and username not in response.text, (
                "Sanitization failed"
            )
            if expected == 200 and not question.lower().startswith("confirm"):
                assert response.json()["observations"] and all(
                    r["status"] == "ok" for r in response.json()["observations"]
                ), "Read-tool projection did not return valid observations"
            return response

        with httpx.Client(
            base_url=base, timeout=30, trust_env=False, headers={"Origin": base}
        ) as guest:
            token = guest.get("/api/auth/session").json()["csrfToken"]
            ask(guest, token, "List profiles", expected=401)
        operator, csrf = login()
        with closing(operator):
            ask(operator, csrf, "List integration profiles")
            ask(operator, csrf, "List imports")
            ask(operator, csrf, "Inspect import job " + JOB)
            ask(operator, csrf, "Get reconciliation report for " + JOB)
            ask(
                operator,
                csrf,
                "Search supplier knowledge encoding",
                collection_ids=["ed76d914-7c66-5102-9178-676334063938"],
            )
            handoff = ask(operator, csrf, "Confirm import " + JOB)
            assert handoff.json()["result"]["kind"] == "handoff"
            ask(operator, "stale", "List imports", expected=403)
            with sql_connect() as c:
                c.execute("UPDATE auth_account SET role='VIEWER' WHERE username=%s", (username,))
            ask(operator, csrf, "List imports", expected=403)
            with sql_connect() as c:
                c.execute(
                    "UPDATE auth_account SET role='OPERATOR',enabled=false WHERE username=%s",
                    (username,),
                )
            ask(operator, csrf, "List imports", expected=401)
        with sql_connect() as c:
            c.execute("UPDATE auth_account SET enabled=true WHERE username=%s", (username,))
        operator, csrf = login()
        with closing(operator):
            with sql_connect() as c:
                c.execute(
                    "UPDATE spring_session SET expiry_time=1,last_access_time=1 "
                    "WHERE principal_name=%s",
                    (username,),
                )
            ask(operator, csrf, "List imports", expected=401)
        operator, csrf = login()
        with closing(operator):
            with sql_connect() as c:
                c.execute("DELETE FROM auth_account WHERE username=%s", (username,))
            ask(operator, csrf, "List imports", expected=401)
        with sql_connect() as c:
            after = snapshot(c)
        assert before == after, "Business state changed during read-only checks"
        report.update(
            status="PASS",
            business_table_snapshots_unchanged=True,
            business_before=before,
            business_after=after,
            keys="ephemeral_process_only",
            java_provider="real_disposable_Java",
            agent_planner="fake",
            retrieval="real_local_E5_and_AI_PostgreSQL",
        )
    except Exception as failure:
        report.update(
            status="FAIL", failure_type=type(failure).__name__, private_logs=str(temporary)
        )
        raise
    finally:
        for process in reversed(processes):
            if os.name == "nt" and process.poll() is None:
                # Kill only the PID tree created by this runner, including Java/venv redirectors.
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in files:
            log.close()
        for name in reversed(containers):
            assert name.startswith(("vmarket-p09-pg-", "vmarket-p09-redis-"))
            command(["docker", "rm", "--force", name])
        output.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(report, indent=2) + "\n"
        assert all(
            secret not in text
            for secret in (private_der, bff_secret, ops_secret, actor_key, password, password_hash)
        )
        output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        main(args.project2, args.output)
        print("LOCAL_P09_SMOKE_PASS")
    except Exception as failure:
        print("LOCAL_P09_SMOKE_FAILED", type(failure).__name__)
        raise SystemExit(1) from None
