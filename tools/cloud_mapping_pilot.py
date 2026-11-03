"""Recompute a frozen synthetic pilot; never infer human productivity from these scores."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "evals/cloud-mapping/pilot-v1"
TARGETS = ("sku", "name", "on_hand")


def report(directory: Path = DATA) -> dict:
    raw = (directory / "cases.json").read_bytes()
    freeze = json.loads((directory / "freeze.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != freeze["cases_sha256"]:
        raise ValueError("Frozen case bytes changed")
    cases = json.loads(raw)
    by_id = {case["id"]: case for case in cases}
    summaries, predictions = {}, {}
    artifacts = {"cases.json": hashlib.sha256(raw).hexdigest()}
    for arm in ("baseline", "candidate"):
        path = directory / f"{arm}-raw.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        if len(rows) != len(cases) or {r["id"] for r in rows} != set(by_id):
            raise ValueError(f"Incomplete or duplicate observations: {arm}")
        artifacts[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        scores = []
        for row in rows:
            case = by_id[row["id"]]
            draft = row.get("response", {}).get("draft", {})
            assigned = {a["target_field"]: a["source_header"] for a in draft.get("assignments", [])}
            if len(assigned) != len(draft.get("assignments", [])):
                raise ValueError("Duplicate target")
            expected = case["expected"]
            valid = row["status"] == 200
            scores.append(
                {
                    "id": row["id"],
                    "status": row["status"],
                    "exact": valid and all(assigned.get(t) == expected[t] for t in TARGETS),
                    "complete_expected": all(expected[t] is not None for t in TARGETS),
                    "proposed_pairs": len(assigned),
                    "correct_pairs": sum(expected[t] == h for t, h in assigned.items()),
                    "incorrect_pairs": sum(expected[t] != h for t, h in assigned.items()),
                    "required_pair_changes": sum(assigned.get(t) != expected[t] for t in TARGETS),
                    "missing_supported_pairs": sum(
                        expected[t] is not None and t not in assigned for t in TARGETS
                    ),
                    "model_attempt": draft.get("reason") == "MODEL_DRAFT_REQUIRES_REVIEW",
                    "ms": row["ms"],
                }
            )
        complete = [s for s in scores if s["complete_expected"]]
        partial = [s for s in scores if not s["complete_expected"]]
        summaries[arm] = {
            "cases": len(scores),
            "http_success": sum(s["status"] == 200 for s in scores),
            "exact_all_cases": sum(s["exact"] for s in scores),
            "complete_mapping_cases": len(complete),
            "exact_complete_mappings": sum(s["exact"] for s in complete),
            "partial_or_ambiguous_cases": len(partial),
            "exact_partial_or_ambiguous": sum(s["exact"] for s in partial),
            **{
                key: sum(s[key] for s in scores)
                for key in (
                    "proposed_pairs",
                    "correct_pairs",
                    "incorrect_pairs",
                    "required_pair_changes",
                    "missing_supported_pairs",
                    "model_attempt",
                )
            },
        }
        predictions[arm] = scores
    old, new = summaries["baseline"], summaries["candidate"]
    return {
        "scope": (
            f"{len(cases)} synthetic developer-authored paired diagnostic cases; "
            "not independent held-out acceptance"
        ),
        "model": freeze["model"],
        "human_time_saving": "NOT_MEASURED",
        "pair_changes": (
            "Minimum pair changes relative to provisional labels; not observed human edits"
        ),
        "promotion_gate": new["http_success"] == len(cases)
        and new["incorrect_pairs"] <= old["incorrect_pairs"]
        and new["exact_complete_mappings"] >= old["exact_complete_mappings"],
        "summary": summaries,
        "predictions": predictions,
        "artifacts_sha256": artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--directory", default="evals/cloud-mapping/pilot-v1")
    args = parser.parse_args()
    directory = ROOT / args.directory
    result = report(directory)
    target = directory / "report.json"
    if args.check:
        if json.loads(target.read_text(encoding="utf-8")) != result:
            raise ValueError("Recorded scores differ from recomputed observations")
    else:
        target.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    print(json.dumps({"promotion_gate": result["promotion_gate"], "summary": result["summary"]}))


if __name__ == "__main__":
    main()
