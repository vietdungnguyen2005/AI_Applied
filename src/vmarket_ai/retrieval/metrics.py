import math
from statistics import median


def ranked_metrics(ranked: list[str], relevance: dict[str, int], k: int) -> dict[str, float | None]:
    if k < 1 or len(ranked) != len(set(ranked)) or any(g < 0 for g in relevance.values()):
        raise ValueError("Invalid ranked evaluation input")
    positive = {key: grade for key, grade in relevance.items() if grade > 0}
    if not positive:
        return {name: None for name in ("hit", "recall", "mrr", "ndcg")}
    selected = ranked[:k]
    found = [i for i, key in enumerate(selected, 1) if key in positive]
    dcg = sum(
        (2 ** positive.get(key, 0) - 1) / math.log2(i + 1) for i, key in enumerate(selected, 1)
    )
    ideal = sum(
        (2**grade - 1) / math.log2(i + 1)
        for i, grade in enumerate(sorted(positive.values(), reverse=True)[:k], 1)
    )
    return {
        "hit": float(bool(found)),
        "recall": len(found) / len(positive),
        "mrr": 1 / found[0] if found else 0.0,
        "ndcg": dcg / ideal,
    }


def latency(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Invalid timings")
    ordered = sorted(values)
    at = (len(ordered) - 1) * 0.95
    lo, hi = math.floor(at), math.ceil(at)
    p95 = ordered[lo] + (ordered[hi] - ordered[lo]) * (at - lo)
    return {"median_ms": median(ordered), "p95_ms": p95}
