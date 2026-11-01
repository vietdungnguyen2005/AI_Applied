"""Disposable P10 acceptance: real signed draft, human browser and DB invariants."""

import base64
import hashlib
import hmac
import json
import os
import subprocess
import time
from contextlib import closing

import httpx


def exercise(
    *,
    operator_login,
    sql_connect,
    snapshot,
    report,
    base,
    project2,
    username,
    password,
    ops_secret,
    output_dir,
    java,
    java_env,
    start,
):
    operator, csrf = operator_login()
    with closing(operator):
        raw = b"SKU,ProductName,AvailableQuantity\nVM-002,Fault test desk,60\n"
        headers = {"X-CSRF-TOKEN": csrf}
        csv_headers = {**headers, "Content-Type": "text/csv"}

        def snap():
            with sql_connect() as c:
                return snapshot(c)

        def rejected(name, action, expected):
            before = snap()
            response = action()
            assert response.status_code == expected, (name, response.status_code)
            after = snap()
            assert before == after, name + " changed business tables"
            report["checks"].append(
                {
                    "name": name,
                    "http": expected,
                    "unchanged_11_tables": True,
                    "before": before,
                    "after": after,
                }
            )

        before = snap()
        response = operator.post(
            "/api/ops/ai/mapping/suggest",
            json={
                "raw_base64": base64.b64encode(raw).decode(),
                "declared_encoding": "UTF-8",
                "source_profile_id": "supplier-b",
                "source_profile_version": 1,
                "method": "rule",
                "synthetic": True,
            },
            headers=headers,
        )
        assert response.status_code == 200, "Signed draft failed"
        draft = response.json()["draft"]
        assert (
            draft["vendor_verification"] == "bff_profile_snapshot"
            and draft["requires_human_acceptance"]
        )
        assert before == snap()
        report["checks"].append(
            {
                "name": "signed_draft_readonly",
                "http": 200,
                "raw_sha256": draft["raw_sha256"],
                "unchanged_11_tables": True,
                "before": before,
                "after": snap(),
            }
        )
        template = operator.get("/api/ops/integration-profiles").json()[0]
        template = next(
            p
            for p in operator.get("/api/ops/integration-profiles").json()
            if p["profileId"] == "supplier-b"
        )
        definition = {
            k: template[k] for k in ("encoding", "vendorCode", "mapping", "skuNormalization")
        }
        definition.update(profileId="fault-valid", version=1)
        published = operator.post("/api/ops/integration-profiles", json=definition, headers=headers)
        assert published.status_code == 201 and published.json()["active"] is False
        assert (
            operator.patch(
                "/api/ops/integration-profiles/fault-valid/1",
                json={"active": True},
                headers=headers,
            ).status_code
            == 200
        )
        path = "/api/ops/onboarding/fault-valid/1/"

        def preview():
            response = operator.post(path + "preview", content=raw, headers=csv_headers)
            assert response.status_code == 200 and response.json()["acceptedRows"] == 1
            return response.json()["confirmationReceipt"]

        def confirm(receipt, body=raw, csrf_value=csrf):
            return operator.post(
                path + "confirm",
                content=body,
                headers={
                    **csv_headers,
                    "X-CSRF-TOKEN": csrf_value,
                    "X-Source-Name": "fault.csv",
                    "X-Preview-Receipt": receipt,
                },
            )

        receipt = preview()
        rejected("tampered_original", lambda: confirm(receipt, raw + b"\n"), 409)
        rejected("stale_csrf", lambda: confirm(receipt, csrf_value="stale"), 403)
        rejected(
            "missing_csrf",
            lambda: operator.post(
                path + "confirm",
                content=raw,
                headers={
                    "Content-Type": "text/csv",
                    "X-Source-Name": "fault.csv",
                    "X-Preview-Receipt": receipt,
                },
            ),
            403,
        )
        with httpx.Client(
            base_url=base, timeout=30, trust_env=False, headers={"Origin": base}
        ) as guest:
            guest_csrf = guest.get("/api/auth/session").json()["csrfToken"]
            rejected(
                "guest_confirm",
                lambda: guest.post(
                    path + "confirm",
                    content=raw,
                    headers={
                        "Content-Type": "text/csv",
                        "X-Source-Name": "fault.csv",
                        "X-Preview-Receipt": receipt,
                        "X-CSRF-TOKEN": guest_csrf,
                    },
                ),
                401,
            )
        fields = receipt.split(":")
        fields[0] = str(int(time.time()) - 1)
        payload = ":".join(fields[:3])
        message = (
            "vmarket-supplier-preview:v1:fault-valid:1:"
            + hashlib.sha256(username.encode()).hexdigest()
            + ":"
            + payload
        )
        expired = (
            payload + ":" + hmac.new(ops_secret.encode(), message.encode(), "sha256").hexdigest()
        )
        rejected("controlled_valid_signature_expired_receipt", lambda: confirm(expired), 409)
        operator.patch(
            "/api/ops/integration-profiles/fault-valid/1", json={"active": False}, headers=headers
        ).raise_for_status()
        rejected("deactivated_after_preview", lambda: confirm(receipt), 409)
        operator.patch(
            "/api/ops/integration-profiles/fault-valid/1", json={"active": True}, headers=headers
        ).raise_for_status()
        receipt = preview()
        with sql_connect() as c:
            c.execute(
                "UPDATE inventory_stock SET version=version+1 "
                "WHERE product_id=(SELECT id FROM product WHERE sku='VM-002')"
            )
        rejected("stock_changed_after_preview", lambda: confirm(receipt), 409)
        receipt = preview()
        with sql_connect() as c:
            c.execute("UPDATE product SET version=version+1 WHERE sku='VM-002'")
        rejected("product_changed_after_preview", lambda: confirm(receipt), 409)
        wrong = {
            **definition,
            "profileId": "fault-wrong",
            "mapping": {"sku": "ProductName", "name": "SKU", "on_hand": "AvailableQuantity"},
        }
        operator.post(
            "/api/ops/integration-profiles", json=wrong, headers=headers
        ).raise_for_status()
        operator.patch(
            "/api/ops/integration-profiles/fault-wrong/1", json={"active": True}, headers=headers
        ).raise_for_status()
        bad_preview = operator.post(
            "/api/ops/onboarding/fault-wrong/1/preview", content=raw, headers=csv_headers
        )
        assert bad_preview.status_code == 200 and bad_preview.json()["acceptedRows"] == 0
        rejected(
            "wrong_mapping_no_acceptable_rows",
            lambda: operator.post(
                "/api/ops/onboarding/fault-wrong/1/confirm",
                content=raw,
                headers={
                    **csv_headers,
                    "X-Source-Name": "fault.csv",
                    "X-Preview-Receipt": bad_preview.json()["confirmationReceipt"],
                },
            ),
            400,
        )
        browser_before = snap()
        child = subprocess.run(
            ["python", str(project2 / "tools/qa_mapping_real.py")],
            input=json.dumps(
                {
                    "base": base,
                    "username": username,
                    "password": password,
                    "output": str(output_dir / "P10b-real-browser"),
                }
            ),
            capture_output=True,
            text=True,
            timeout=150,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if child.returncode:
            # Exception names/line locations are useful, credentials are never echoed.
            print(
                child.stderr.replace(password, "[REDACTED]").replace(username, "[OPERATOR]"),
                flush=True,
            )
            raise RuntimeError("Real browser acceptance failed")
        browser = json.loads(child.stdout)
        after_browser = snap()
        assert browser["status"] == "PASS" and len(browser["records"]) == 2
        assert (
            browser_before["inventory_movement"] == after_browser["inventory_movement"]
            and browser_before["inventory_stock"] == after_browser["inventory_stock"]
        )
        assert after_browser["migration_job"][0] - browser_before["migration_job"][0] == 2
        assert (
            after_browser["integration_profile"][0] - browser_before["integration_profile"][0] == 2
        )
        report["browser"] = browser
        report["pending_stock_unchanged"] = True
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(java.pid), "/T", "/F"], check=True, capture_output=True
            )
        else:
            java.terminate()
        java.wait(timeout=10)
        env = {**java_env, "IMPORT_WORKER_ENABLED": "true"}
        java2 = start(
            "java-worker",
            [
                "java",
                "-jar",
                "backend/target/v-market-backend-0.1.0-SNAPSHOT.jar",
                "--server.port=18093",
            ],
            env,
            project2,
        )
        from p10_local_smoke import wait_http

        wait_http("http://127.0.0.1:18093/actuator/health", java2)
        for record in browser["records"]:
            until = time.monotonic() + 40
            while time.monotonic() < until:
                job = operator.get("/api/ops/imports/" + record["job_id"] + "/inspection").json()[
                    "job"
                ]
                if job["status"] not in {"STAGED", "RUNNING"}:
                    break
                time.sleep(0.3)
            assert job["status"] == "COMPLETED" and job["appliedRows"] == 1
            record["terminal_status"] = job["status"]
        applied = snap()
        for record in browser["records"]:
            original = base64.b64decode(record["raw_base64"])
            route = "/api/ops/onboarding/" + record["profile_id"] + "/1/"
            preview_response = operator.post(
                route + "preview", content=original, headers=csv_headers
            )
            assert preview_response.status_code == 200
            duplicate = operator.post(
                route + "confirm",
                content=original,
                headers={
                    **csv_headers,
                    "X-Source-Name": "terminal-retry.csv",
                    "X-Preview-Receipt": preview_response.json()["confirmationReceipt"],
                },
            )
            assert duplicate.status_code == 202 and duplicate.json()["id"] == record["job_id"]
            assert duplicate.json()["status"] == "COMPLETED"
        assert applied == snap(), "Completed replay changed business state"
        with sql_connect() as c:
            stock = c.execute(
                "SELECT p.sku,s.on_hand FROM inventory_stock s JOIN product p "
                "ON p.id=s.product_id WHERE p.sku IN ('VM-001','VM-002') ORDER BY p.sku"
            ).fetchall()
        assert stock == [("VM-001", 32), ("VM-002", 60)]
        report["completed_replay"] = {
            "same_job_ids": True,
            "unchanged_11_tables": True,
            "before": applied,
            "after": snap(),
            "observed_stock": stock,
        }
        report.update(
            status="PASS",
            keys="ephemeral_process_only",
            java="real_disposable",
            ai="fake_rule_no_external_inference",
            fault_injection="owned_disposable_database_only",
        )
