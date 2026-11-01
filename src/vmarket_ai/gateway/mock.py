from datetime import UTC, datetime
from typing import Any

from vmarket_ai.gateway.agent import AgentService
from vmarket_ai.gateway.wire import validate
from vmarket_ai.mapping.policy import PROFILES

JOB = "11111111-1111-4111-8111-111111111111"


def execute(intent: dict[str, Any]) -> dict[str, Any]:
    name = intent["tool_name"]
    result = {
        "call_id": intent["call_id"],
        "tool_name": name,
        "status": "ok",
        "observed_at": datetime.now(UTC).isoformat(),
        "truncated": False,
        "error_code": None,
        "data": None,
    }
    job = {
        "job_id": JOB,
        "status": "FAILED",
        "total_rows": 1,
        "valid_rows": 0,
        "applied_rows": 0,
        "rejected_rows": 1,
        "checkpoint_row": 0,
        "import_mode": "METADATA_ONLY",
        "profile_id": None,
        "profile_version": None,
    }
    if name == "get_integration_profiles":
        result["data"] = {
            "profiles": [
                {
                    **p.model_dump(exclude={"mapping"}),
                    "mapping": dict(p.mapping),
                    "sku_normalization": "TRIM_UPPER",
                    "required_fields": ["sku", "name", "on_hand"],
                }
                for p in PROFILES
            ]
        }
    elif name == "get_imports":
        result["data"] = {"imports": [job]}
    elif name == "search_supplier_knowledge":
        result["data"] = {"hits": []}
    elif intent["arguments"]["job_id"] != JOB:
        result.update(status="unavailable", error_code="UPSTREAM_RESOURCE_UNAVAILABLE")
    elif name == "inspect_import_job":
        result["data"] = {
            "job": job,
            "work_state": "FAILED",
            "recovery_count": 0,
            "restart_allowed": True,
            "errors": [{"row_number": 2, "code": "UNKNOWN_SKU"}],
        }
    else:
        result["data"] = {
            "report_id": "22222222-2222-4222-8222-222222222222",
            "job_id": JOB,
            "status": "COMPLETED",
            "mismatch_count": 0,
            "changed_since_import_rows": 0,
            "stock_not_verified_rows": 1,
            "discrepancies": [],
        }
    validate("ToolResult", result)
    return result


async def run(service: AgentService, payload: dict[str, Any]) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    for step in range(4):
        response = await service.step(
            {
                **payload,
                "step": step,
                "tool_result": history[-1] if history else None,
                "previous_results": history[:-1],
            }
        )
        if response["kind"] != "tool_intent":
            return {"result": response, "observations": history, "source_mode": "synthetic_mock"}
        history.append(execute(response["intent"]))
    raise RuntimeError("Unreachable bounded mock loop")
