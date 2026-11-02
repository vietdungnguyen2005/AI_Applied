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


def main(
    project2: Path, output: Path, *, qa=False, mapping=False, checks=None, container_image=None
):
    if container_image and (qa or mapping):
        raise ValueError("Signed private-container mode supports fake read-only tools only")
    if output.exists():
        raise ValueError("A fresh evidence filename is required")
    project2 = project2.resolve()
    for port in (18094, 18095, 13014, 8094):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("Reserved QA port is already occupied")
    temporary = ROOT / ".local" / ("p11-smoke-" + uuid4().hex[:8])
    temporary.mkdir(parents=True)
    pg = "vmarket-p11-pg-" + uuid4().hex[:8]
    redis = "vmarket-p11-redis-" + uuid4().hex[:8]
    containers, processes, files, networks = [], [], [], []
    proxy = None
    report = {"mode": "disposable_local_integration", "external_provider_calls": 0, "checks": []}
    report["source_commit"] = command(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    report["project2_commit"] = command(["git", "rev-parse", "HEAD"], cwd=project2).decode().strip()
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
    username = "p11-operator@example.test"
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
            password="p11-disposable-db-only",
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
                "POSTGRES_PASSWORD=p11-disposable-db-only",
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
            "SPRING_DATASOURCE_PASSWORD": "p11-disposable-db-only",
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
                "--server.port=18094",
            ],
            java_env,
            project2,
        )
        wait_http("http://127.0.0.1:18094/actuator/health", java)
        ai_pg = "vmarket-p11-aipg-" + uuid4().hex[:8]
        command(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "--name",
                ai_pg,
                "-e",
                "POSTGRES_DB=vmarket_ai_test",
                "-e",
                "POSTGRES_USER=ai_owner",
                "-e",
                "POSTGRES_PASSWORD=local-ai-owner-only",
                "-p",
                "127.0.0.1::5432",
                "-v",
                str(ROOT / "docker/init-ai.sql") + ":/docker-entrypoint-initdb.d/10-ai.sql:ro",
                "pgvector/pgvector:pg17",
            ]
        )
        containers.append(ai_pg)
        ai_port = command(["docker", "port", ai_pg, "5432"]).decode().strip().rsplit(":", 1)[1]
        for _attempt in range(100):
            try:
                with psycopg.connect(
                    host="127.0.0.1",
                    port=ai_port,
                    dbname="vmarket_ai_test",
                    user="ai_owner",
                    password="local-ai-owner-only",
                    connect_timeout=1,
                ):
                    pass
                break
            except psycopg.OperationalError:
                time.sleep(0.2)
        from p11_proxy import ReadProxy

        proxy = ReadProxy(18095, "http://127.0.0.1:18094")
        proxy.start()
        ai_env = {
            **base_env,
            "AI_MODE": "integrated",
            "AI_AGENT_ENABLED": "true",
            "AI_QA_ENABLED": "false",
            "AI_MAPPING_ENABLED": "true" if mapping else "false",
            "AI_RUNS_ENABLED": "true",
            "AI_PROVIDER_MODE": "fake",
            "AI_LIVE_ENABLED": "false",
            "AI_PORT": "8094",
            "AI_BIND_HOST": "127.0.0.1",
            "AI_PRIVATE_CONTAINER": "false",
            "AI_REQUEST_DEADLINE_SECONDS": "25",
            "AI_DATABASE_URL": f"postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:{ai_port}/vmarket_ai_test",
            "AI_QA_EMBEDDING_MODE": "fake",
            "AI_QA_MODEL_BUNDLE": str(ROOT / ".local/models/multilingual-e5-small"),
            "AI_GATEWAY_PUBLIC_KEYS": json.dumps({"p11-ephemeral": public_raw}),
        }
        if qa:
            ai_env.update(AI_QA_ENABLED="true", AI_QA_EMBEDDING_MODE="local")
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
            "AI_MIGRATION_DATABASE_URL": f"postgresql+psycopg://ai_owner:local-ai-owner-only@127.0.0.1:{ai_port}/vmarket_ai_test",
        }
        command(
            [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "migrate"],
            env=migration_env,
            cwd=ROOT,
        )
        if qa:
            command(
                [
                    sys.executable,
                    "-m",
                    "vmarket_ai.ingestion.demo",
                    "--postgres",
                    "--model-bundle",
                    ai_env["AI_QA_MODEL_BUNDLE"],
                    "--report",
                    str(temporary / "ingestion.json"),
                ],
                env=migration_env,
                cwd=ROOT,
            )
        if container_image:
            network = "vmarket-p15-net-" + uuid4().hex[:8]
            command(["docker", "network", "create", network])
            networks.append(network)
            command(["docker", "network", "connect", network, ai_pg])
            container = "vmarket-p15-ai-" + uuid4().hex[:8]
            env_values = {
                "AI_MODE": "integrated",
                "AI_AGENT_ENABLED": "true",
                "AI_RUNS_ENABLED": "true",
                "AI_PROVIDER_MODE": "fake",
                "AI_LIVE_ENABLED": "false",
                "AI_PORT": "8094",
                "AI_PRIVATE_CONTAINER": "true",
                "AI_SIGNED_CONTAINER": "true",
                "AI_BIND_HOST": "0.0.0.0",
                "AI_REQUEST_DEADLINE_SECONDS": "25",
                "AI_GATEWAY_PUBLIC_KEYS": ai_env["AI_GATEWAY_PUBLIC_KEYS"],
                "AI_DATABASE_URL": f"postgresql+psycopg://ai_app:local-ai-app-only@{ai_pg}:5432/vmarket_ai_test",
            }
            arguments = [
                "docker",
                "run",
                "-d",
                "--name",
                container,
                "--network",
                network,
                "--read-only",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "-p",
                "127.0.0.1:8094:8094",
            ]
            for name, value in env_values.items():
                arguments.extend(["-e", name + "=" + value])
            command([*arguments, container_image])
            containers.append(container)
            details = json.loads(command(["docker", "inspect", container]))[0]
            assert details["HostConfig"]["PortBindings"]["8094/tcp"][0]["HostIp"] == "127.0.0.1"
            serialized = json.dumps(details["Config"]["Env"])
            assert all(
                s not in serialized
                for s in (private_der, bff_secret, ops_secret, actor_key, password)
            )
            report["container"] = {
                "image": details["Image"],
                "loopback_published": True,
                "private_network": True,
                "network_internal": False,
                "read_only": True,
                "memory_bytes": 536870912,
                "cpus": 1,
                "no_java_signing_or_provider_secrets": True,
            }
            ai = start("ai", ["docker", "logs", "--follow", container], base_env, ROOT)
        else:
            ai = start(
                "ai",
                [sys.executable, "-c", "from vmarket_ai.cli import main;main()", "serve"],
                ai_env,
                ROOT,
            )
        wait_http("http://127.0.0.1:8094/ready", ai)
        bff_env = {
            **base_env,
            "BACKEND_ORIGIN": "http://127.0.0.1:18095",
            "BFF_SHARED_SECRET": bff_secret,
            "VMARKET_OPS_SECRET": ops_secret,
            "AI_COPILOT_ENABLED": "true",
            "AI_MAPPING_DRAFTS_ENABLED": "true" if mapping else "false",
            "AI_RUNS_ENABLED": "true",
            "AI_SERVICE_ORIGIN": "http://127.0.0.1:8094",
            "AI_SIGNING_KID": "p11-ephemeral",
            "AI_SIGNING_KEY_PKCS8_BASE64": private_der,
            "AI_ACTOR_HMAC_KEY": actor_key,
        }
        if qa:
            bff_env.update(AI_QA_ENABLED="true", AI_COPILOT_PANEL_ENABLED="true")
        bff = start(
            "bff",
            [
                "node",
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                "13014",
            ],
            bff_env,
            project2,
        )
        base = "http://127.0.0.1:13014"
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

        def restart(name, old, env, cwd, args):
            if old.poll() is None:
                if os.name == "nt":
                    command(["taskkill", "/PID", str(old.pid), "/T", "/F"])
                else:
                    old.terminate()
                old.wait(timeout=10)
            return start(name, args, env, cwd)

        def provider(mode):
            nonlocal ai
            assert mode in {"local", "fake"}
            ai_env["AI_PROVIDER_MODE"] = mode
            ai = restart("ai-" + mode, ai, ai_env, ROOT, ai.args)
            wait_http("http://127.0.0.1:8094/ready", ai)

        def restart_owned_ai():
            nonlocal ai
            if container_image:
                command(["docker", "restart", container])
                ai = restart("ai-restarted", ai, base_env, ROOT, ai.args)
                wait_http("http://127.0.0.1:8094/ready", ai)
                return ai
            return restart("ai-restarted", ai, ai_env, ROOT, ai.args)

        if checks is None:
            from p11_checks import exercise

            checks = exercise
        options = {"provider": provider, "project2": project2} if qa else {}
        if container_image:
            options["stop_ai"] = lambda: command(["docker", "stop", container])
        checks(
            operator_login=login,
            sql_connect=sql_connect,
            snapshot=snapshot,
            report=report,
            base=base,
            proxy=proxy,
            ai_port=ai_port,
            migration_env=migration_env,
            username=username,
            restart_ai=restart_owned_ai,
            restart_bff=lambda: restart("bff-restarted", bff, bff_env, project2, bff.args),
            **options,
        )
    except Exception as failure:
        report.update(
            status="FAIL", failure_type=type(failure).__name__, private_logs=str(temporary)
        )
        raise
    finally:
        if proxy is not None:
            proxy.close()
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
            assert name.startswith(
                ("vmarket-p11-pg-", "vmarket-p11-redis-", "vmarket-p11-aipg-", "vmarket-p15-ai-")
            )
            command(["docker", "rm", "--force", name])
        for network in reversed(networks):
            assert network.startswith("vmarket-p15-net-")
            command(["docker", "network", "rm", network])
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
        print("LOCAL_P11_SMOKE_PASS")
    except Exception as failure:
        print("LOCAL_P11_SMOKE_FAILED", type(failure).__name__)
        raise SystemExit(1) from None
