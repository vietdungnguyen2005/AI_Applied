"""Real disposable Java/BFF signed-profile reuse; no model inference or business import."""

import argparse
import base64
import hashlib
from contextlib import closing
from pathlib import Path

from p11_local_smoke import main


def exercise(*, operator_login, sql_connect, snapshot, report, **unused):
    operator, csrf = operator_login()
    raw = b"PartnerRef,PublicLabel,CountAtDock\nVM-002,Reviewed desk,9\n"
    mapping = {"sku": "PartnerRef", "name": "PublicLabel", "on_hand": "CountAtDock"}
    with closing(operator):
        headers = {"X-CSRF-TOKEN": csrf}
        # Explicit operator fixture setup. Snapshot comparisons start afterwards.
        profile = {
            "profileId": "reviewed-columns",
            "version": 1,
            "encoding": "UTF-8",
            "vendorCode": "RIVERBYTE",
            "mapping": mapping,
            "skuNormalization": "TRIM_UPPER",
        }
        created = operator.post("/api/ops/integration-profiles", json=profile, headers=headers)
        assert created.status_code == 201 and not created.json()["active"]
        active = operator.patch(
            "/api/ops/integration-profiles/reviewed-columns/1",
            json={"active": True},
            headers=headers,
        )
        assert active.status_code == 200
        with sql_connect() as connection:
            before = snapshot(connection)
        outcomes = []
        for method in ("rule", "ai"):
            body = {
                "raw_base64": base64.b64encode(raw).decode(),
                "declared_encoding": "UTF-8",
                "source_profile_id": "reviewed-columns",
                "source_profile_version": 1,
                "method": method,
                "synthetic": True,
            }
            response = operator.post("/api/ops/ai/mapping/suggest", json=body, headers=headers)
            assert response.status_code == 200, (method, response.status_code)
            draft = response.json()["draft"]
            assert draft["reason"] == "SIGNED_PROFILE_BASELINE"
            assert {a["target_field"]: a["source_header"] for a in draft["assignments"]} == mapping
            assert draft["raw_sha256"] == hashlib.sha256(raw).hexdigest()
            assert (
                draft["requires_human_acceptance"]
                and draft["profile_differences"][0]["changes"] == {}
            )
            outcomes.append(
                {
                    "method": method,
                    "http": 200,
                    "reason": draft["reason"],
                    "assignment_count": len(draft["assignments"]),
                    "requires_human_acceptance": True,
                }
            )
        with sql_connect() as connection:
            after = snapshot(connection)
        assert before == after, "Draft reuse changed business tables"
        assert (
            operator.patch(
                "/api/ops/integration-profiles/reviewed-columns/1",
                json={"active": False},
                headers=headers,
            ).status_code
            == 200
        )
        stale = operator.post("/api/ops/ai/mapping/suggest", json=body, headers=headers)
        assert stale.status_code == 409
    report.update(
        status="PASS",
        profile_reuse=outcomes,
        deactivated_profile_http=409,
        business_before=before,
        business_after=after,
        business_unchanged_11_tables=True,
        fixture_setup=(
            "explicit operator publish inactive, activate, then deactivate in disposable Java DB"
        ),
        provider_mode="fake",
        model_calls=0,
        external_provider_calls=0,
        scope="signed reviewed-profile functionality; not unseen semantic mapping quality",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.project2, args.output, mapping=True, checks=exercise)
    print("SIGNED_PROFILE_REUSE_PASS")
