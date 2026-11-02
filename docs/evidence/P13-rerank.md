# P13 exploratory rerank measurement

Date: 2026-11-02 Asia/Bangkok. Frozen design/source revision: `3ffed9a`.
[Protocol](../../evals/p13/rerank-protocol.md).
[Complete artifact](../../evals/p13/runs/rerank-exploratory-v1/).

Executed `python -m uv run --frozen --offline python tools/p13_rerank.py --output
evals/p13/runs/rerank-exploratory-v1`. All 60 retained P06 dev/test observations
produced 120 before/after rankings. No inference or new retrieval occurred.
Production retrieval remains unchanged.

| Partition/method | MRR@5 before | MRR@5 after | Scored/all queries per method |
| --- | --- | --- | --- |
| dev dense | 0.9375 | 0.8375 | 8/8 |
| dev hybrid | 0.9375 | 0.8375 | 8/8 |
| dev lexical | 0.5625 | 0.5625 | 8/8 |
| test dense | 1.0 | 1.0 | 8/12 |
| test hybrid | 1.0 | 1.0 | 8/12 |
| test lexical | 0.625 | 0.625 | 8/12 |

Recall@5 was unchanged in every group: dense/hybrid 1.0, lexical 0.625.
Four test cases per method have no positive gold and are excluded from ranking
means, not scored as perfect retrieval. Full rankings and metrics at 1/3/5 are
retained, including regressions. The rule therefore offers no demonstrated
reason to enable reranking; original `reranker=none` remains in use.

These questions, outputs and provisional agent labels were inspected previously.
Freezing this analysis before execution does not restore blind held-out status.
The algorithm is a character-bigram lexical rule over the same saved top-five
chunks, not a neural cross-encoder or new retrieval pipeline. This experiment
does not measure authorization, production latency, independent human quality,
or improvements beyond the original candidate pool. P13 independent review and
prospective matched ablations remain open.
