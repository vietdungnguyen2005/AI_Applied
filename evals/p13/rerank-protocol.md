# Exploratory rerank regression protocol

Design recorded before executing this reranker, after the original P06 outputs
and provisional labels had already been inspected. This is post-hoc exploratory
analysis, not a newly blinded held-out evaluation. No tuning loop or alternative
reranker selection will be performed on these results.

Use every retained dev-v1 and test-v1 retrieval row, all three methods. Keep these
partitions separate. Training rows are excluded by design. Keep each original
top-five candidate pool and exact saved chunk text. Normalize query and candidate
with Unicode NFC, casefold and alphanumeric filtering, then compute set Jaccard
over character bigrams. Sort descending, retaining original order for ties.
No labels enter the reranking function; the scorer uses existing P06 chunk gold.

Report Recall, MRR and NDCG at 1, 3 and 5; exclude cases without positive labels
from metric means and show both scored/all denominators. Full-pool Recall@5 must
remain unchanged, since reordering cannot recover missing candidates. This is a
cheap lexical reranker, not a cross-encoder or production reranker integration.
No model/provider calls, fresh retrieval, request-latency claims or human-review
claims. Preserve all rankings including regressions. Do not promote the rule to
production based on these already seen cases.

Reproduce with locked dependencies:

```powershell
python -m uv run --frozen python tools/p13_rerank.py --output .local/p13-rerank-repeat
```

The destination must be new. Input canonical-LF hashes, source Git SHA, all
rankings, per-case scores and summary CSV are saved. Source observations remain
in `evals/retrieval/runs/{dev,test}-v1/predictions.jsonl`.
