"""P02 contract QA only; does not implement or test an AI runtime/security handler.

Run in an isolated environment containing openapi-spec-validator, jsonschema and
PyYAML. Network access is not needed once those validation dependencies exist.
"""

import argparse
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate_url
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    contract_dir = ROOT / "docs" / "contracts"
    schema_path = contract_dir / "bff-tool-gateway.schema.json"
    api_path = contract_dir / "openapi.yaml"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    cases = json.loads((contract_dir / "examples" / "cases.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    checks = []

    def record(name, passed, detail):
        checks.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

    # Validator resolves only repository-controlled local schema references.
    validate_url(api_path.resolve().as_uri())
    record("openapi_structure", True, "OpenAPI 3.1.1 and local references validated")
    Draft202012Validator.check_schema(schema)
    record("json_schema_structure", True, f"{len(schema['$defs'])} definitions in Draft 2020-12")
    registry = Registry().with_resource(
        schema_path.resolve().as_uri(), Resource.from_contents(schema)
    )
    ids = [case["id"] for case in cases]
    record("unique_case_ids", len(ids) == len(set(ids)), f"{len(ids)} synthetic schema cases")
    for case in cases:
        validator = Draft202012Validator(
            {"$ref": schema_path.resolve().as_uri() + "#/$defs/" + case["schema"]},
            registry=registry,
            format_checker=FormatChecker(),
        )
        # Do not print invalid payload values: fixtures can contain leak sentinels.
        errors = list(validator.iter_errors(case["payload"]))
        valid = not errors
        record(
            case["id"],
            valid == case["valid"],
            {
                "schema": case["schema"],
                "expected_valid": case["valid"],
                "actual_valid": valid,
                "error_count": len(errors),
            },
        )

    allowed = {
        branch["properties"]["tool_name"]["const"]
        for branch in schema["$defs"]["ToolIntent"]["oneOf"]
    }
    record(
        "closed_tool_registry",
        allowed
        == {
            "get_integration_profiles",
            "get_imports",
            "inspect_import_job",
            "get_reconciliation_report",
            "search_supplier_knowledge",
        },
        sorted(allowed),
    )
    api = yaml.safe_load(api_path.read_text(encoding="utf-8"))
    methods = [
        (path, method, op) for path, item in api["paths"].items() for method, op in item.items()
    ]
    record(
        "no_http_eval_or_business_mutation",
        "/ai/evals" not in api["paths"]
        and all(
            method in {"get", "post"} and "/api/ops/" not in path for path, method, _ in methods
        ),
        "AI-owned POST endpoints do not represent Java business writes",
    )
    secured = [(path, op) for path, _, op in methods if path.startswith("/ai/")]
    record(
        "integrated_context_security",
        all(
            op.get("security", api["security"]) == [{"AIContext": [], "AISignature": []}]
            and op.get("x-implementation-status")
            == (
                "implemented-opt-in"
                if path
                in {"/ai/mapping/suggest", "/ai/runs/control", "/ai/ask", "/ai/citations/read"}
                else "planned"
            )
            for path, op in secured
        ),
        "Protected routes declare signed context; runtime enforcement tested separately",
    )
    record(
        "transport_byte_budgets",
        all(
            op["x-runtime-max-body-bytes"]
            == (
                6_700_000
                if path == "/ai/mapping/suggest"
                else 5_000_000
                if path == "/ai/documents"
                else 65_536
            )
            for path, op in secured
        ),
        "Declared extensions only; runtime streaming enforcement not tested",
    )
    report = {
        "phase": "P02",
        "scope": "schema and contract design validation only",
        "checks": checks,
        "summary": {
            "checks": len(checks),
            "passed": sum(c["result"] == "PASS" for c in checks),
            "failed": sum(c["result"] == "FAIL" for c in checks),
            "example_cases": len(cases),
            "expected_valid": sum(c["valid"] for c in cases),
            "expected_invalid": sum(not c["valid"] for c in cases),
        },
        "not_tested": [
            "cryptographic signatures",
            "clock/replay enforcement",
            "live operator authorization",
            "scope membership",
            "runtime byte/row limits",
            "Java DB nonmutation",
            "provider quality or spend",
            "browser behavior",
        ],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for check in checks:
        print(json.dumps(check, ensure_ascii=True))
    print("SUMMARY " + json.dumps(report["summary"]))
    raise SystemExit(1 if report["summary"]["failed"] else 0)


if __name__ == "__main__":
    main()
