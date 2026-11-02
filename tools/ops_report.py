"""Metadata-only summary of retained eval observations; never a live traffic dashboard."""

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from vmarket_ai.retrieval.metrics import latency


def summarize(predictions):
    groups = defaultdict(list)
    for row in predictions:
        groups[(row["domain"], row["method"])].append(row)
    output = []
    for (domain, method), rows in sorted(groups.items()):
        quality = {}
        fields = {
            key
            for row in rows
            for key, value in row.get("score", {}).items()
            if isinstance(value, bool)
        }
        for field in sorted(fields):
            measured = [
                r["score"][field] for r in rows if isinstance(r.get("score", {}).get(field), bool)
            ]
            quality[field] = {
                "true": sum(measured),
                "n": len(measured),
                "rate": sum(measured) / len(measured),
            }
        outcomes = [r for r in rows if "http_status" in r or "status" in r]
        failures = sum(
            r.get("http_status", 200) != 200
            or r.get("status")
            in {
                "error",
                "input_error",
                "unavailable",
                "denied",
                "invalid",
                "timeout",
                "budget_exceeded",
            }
            for r in outcomes
        )
        model_outputs = [m for r in rows for m in r.get("model_outputs", [])]
        costs = [Decimal(str(m["cost_usd"])) for m in model_outputs if "cost_usd" in m]
        output.append(
            {
                "domain": domain,
                "method": method,
                "observations": len(rows),
                "request_error_rate": failures / len(outcomes) if outcomes else None,
                "tool_fail_rate": failures / len(outcomes)
                if domain == "tool" and outcomes
                else None,
                "quality_proxies": quality,
                "latency_all_outcomes": latency([r["latency_ms"] for r in rows]),
                "returned_model_results": len(model_outputs),
                "returned_prompt_tokens": sum(m["prompt_tokens"] for m in model_outputs),
                "returned_completion_tokens": sum(m["completion_tokens"] for m in model_outputs),
                "provider_cost_from_returned_results_usd": str(sum(costs)) if costs else None,
                "provider_cost_observations": len(costs),
            }
        )
    return {
        "scope": (
            "archived synthetic benchmark observations; "
            "proxies not human quality or live service monitoring"
        ),
        "groups": output,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a fresh output file")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = summarize(report["predictions"])
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"groups": len(result["groups"])}))
