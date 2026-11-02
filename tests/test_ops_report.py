import importlib.util
from pathlib import Path


def test_functional_success_is_not_mapping_correctness_or_zero_unknown_cost():
    spec = importlib.util.spec_from_file_location(
        "ops_report", Path(__file__).resolve().parents[1] / "tools/ops_report.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [
        {
            "domain": "mapping",
            "method": "rule",
            "status": "abstained",
            "latency_ms": 1,
            "score": {"exact_mapping": False},
        },
        {
            "domain": "mapping",
            "method": "rule",
            "status": "error",
            "latency_ms": 2,
            "score": {"exact_mapping": None},
        },
    ]
    group = module.summarize(rows)["groups"][0]
    assert group["request_error_rate"] == 0.5
    assert group["quality_proxies"]["exact_mapping"] == {"true": 0, "n": 1, "rate": 0.0}
    assert group["provider_cost_from_returned_results_usd"] is None
