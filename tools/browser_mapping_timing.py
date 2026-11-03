"""Recompute descriptive agent UI timings; never infer human productivity."""

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evals/onboarding-time"


def summarize(version: str) -> dict:
    directory = BASE / version
    protocol = json.loads((directory / "protocol.json").read_text(encoding="utf-8"))
    raw = (directory / "cases.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != protocol["cases_sha256"]:
        raise ValueError("Frozen input bytes changed")
    cases = {c["id"]: c for c in json.loads(raw)}
    rows = json.loads((directory / "observations.json").read_text(encoding="utf-8"))
    expected = [(p["case"], arm) for p in protocol["order"] for arm in p["arms"]]
    if [(r["case"], r["arm"]) for r in rows] != expected:
        raise ValueError("Missing, duplicate or reordered observations")
    observations = []
    for row in rows:
        if row["elapsed_ms"] != row["ended_ms"] - row["started_ms"]:
            raise ValueError("Inconsistent elapsed time")
        if row["observed_mapping"] != cases[row["case"]]["expected"]:
            raise ValueError("Mapping does not match provisional expected fields")
        if row["status"] != "completed" or not re.search(
            r"1\s+accepted\s*·\s*0\s+rejected", row["preview_text"]
        ):
            raise ValueError("Required Java preview endpoint not reached")
        errors = [e["label"] for e in row["events"] if e["status"] == "error"]
        observations.append(
            {
                "case": row["case"],
                "arm": row["arm"],
                "elapsed_ms": row["elapsed_ms"],
                "instrumentation_errors": errors,
                "manual_column_entries": sum(
                    e["status"] == "ok"
                    and (
                        e["label"].startswith("manual_edit_")
                        or e["label"].startswith("fallback_edit_")
                    )
                    for e in row["events"]
                ),
                "successful_draft_observation": any(
                    e["label"] == "wait_suggestion" and e["status"] == "ok" for e in row["events"]
                ),
            }
        )
    summaries = {}
    for arm in ("manual", "assisted"):
        selected = [r for r in observations if r["arm"] == arm]
        summaries[arm] = {
            "completed_tasks": len(selected),
            "median_elapsed_ms": statistics.median(r["elapsed_ms"] for r in selected),
            "manual_column_entries": sum(r["manual_column_entries"] for r in selected),
            "tasks_with_instrumentation_errors": sum(
                bool(r["instrumentation_errors"]) for r in selected
            ),
            "successful_draft_observations": sum(
                r["successful_draft_observation"] for r in selected
            ),
        }
    return {
        "version": version,
        "scope": (
            "One informed agent, three repeated synthetic files, "
            "real online UI/Java/AI; not human UAT"
        ),
        "time_saving_claim_supported": False,
        "reason": (
            "Instrumentation errors retained; "
            "agent timings do not establish human onboarding savings"
        ),
        "summary": summaries,
        "observations": observations,
        "artifacts_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.iterdir())
            if path.suffix in {".json", ".js", ".png", ".jpg"} and path.name != "report.json"
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for version in ("agent-browser-v2", "agent-browser-v3"):
        result = summarize(version)
        target = BASE / version / "report.json"
        if args.check:
            if json.loads(target.read_text(encoding="utf-8")) != result:
                raise ValueError("Recorded report differs from raw observations")
        else:
            target.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        print(json.dumps({"version": version, "summary": result["summary"]}))


if __name__ == "__main__":
    main()
