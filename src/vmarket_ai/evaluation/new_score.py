"""Deterministic provisional scoring; provider failures never count as wrong answers."""

import statistics
from typing import Any

from vmarket_ai.retrieval.metrics import latency, ranked_metrics


def score_qa(prediction: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    body = prediction.get("response")
    if prediction.get("http_status") != 200 or not isinstance(body, dict):
        return {
            "valid": False,
            "decision_correct": None,
            "anchor_proxy": None,
            "citation_proxy": None,
            "abstain_reason_correct": None,
        }
    expected = label["expected_status"]
    answer = body.get("answer") or ""
    anchors = label["required_answer_anchors"]
    relevant = {(r["document_id"], r["section"]) for r in label["relevant"]}
    citations = {
        (c["document_id"], str(c["locator"]["value"]))
        for c in body.get("citations", [])
        if c.get("locator", {}).get("kind") == "section"
    }
    return {
        "valid": True,
        "decision_correct": body.get("status") == expected,
        "anchor_proxy": all(anchor.casefold() in answer.casefold() for anchor in anchors)
        if expected == "answered"
        else None,
        "citation_proxy": body.get("status") == "answered" and bool(citations & relevant)
        if expected == "answered"
        else None,
        "abstain_reason_correct": body.get("reason") == label["expected_abstain_reason"]
        if expected == "abstained"
        else None,
    }


def score_retrieval(prediction: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    if prediction.get("status") != "ok":
        return {"valid": False, "metrics": None}
    relevant = {f"{r['document_id']}:{r['section']}": 1 for r in label["relevant"]}
    # One document section can contain multiple chunks; do not count it more than once.
    ranked = list(dict.fromkeys(f"{h['document_id']}:{h['section']}" for h in prediction["hits"]))
    return {"valid": True, "metrics": ranked_metrics(ranked, relevant, 5)}


def aggregate(qa: list[dict[str, Any]], retrieval: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []

    def add(domain: str, method: str, metric: str, value: Any, n: int) -> None:
        result.append(
            {"domain": domain, "method": method, "metric": metric, "value": value, "n": n}
        )

    for method in sorted({r["method"] for r in qa}):
        group = [r for r in qa if r["method"] == method]
        valid = [r for r in group if r["score"]["valid"]]
        add("qa", method, "valid_response_coverage", len(valid) / len(group), len(group))
        for field in (
            "decision_correct",
            "anchor_proxy",
            "citation_proxy",
            "abstain_reason_correct",
        ):
            measured = [r["score"][field] for r in valid if r["score"][field] is not None]
            add(
                "qa",
                method,
                field,
                sum(measured) / len(measured) if measured else None,
                len(measured),
            )
        if valid:
            for name, value in latency([r["latency_ms"] for r in valid]).items():
                add("qa", method, name, value, len(valid))
    for method in sorted({r["method"] for r in retrieval}):
        group = [r for r in retrieval if r["method"] == method]
        valid = [r for r in group if r["score"]["valid"]]
        add("retrieval", method, "valid_response_coverage", len(valid) / len(group), len(group))
        for metric in ("recall", "mrr"):
            measured = [
                r["score"]["metrics"][metric]
                for r in valid
                if r["score"]["metrics"][metric] is not None
            ]
            add(
                "retrieval",
                method,
                metric + "@5",
                statistics.mean(measured) if measured else None,
                len(measured),
            )
        if valid:
            for name, value in latency([r["latency_ms"] for r in valid]).items():
                add("retrieval", method, name, value, len(valid))
    return result
