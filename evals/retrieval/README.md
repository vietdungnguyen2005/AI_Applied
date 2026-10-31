# P06 retrieval benchmark

Executed 2026-11-01 Asia/Bangkok, using frozen synthetic policy state as of **2026-10-31**. Results are against **provisional agent-authored labels with independent human review pending**. This is a small, original synthetic corpus, not customer UAT or a production-quality certification.

## Protocol and freeze

- [Config](config.json): pinned local E5 FP32/384, 320-character chunks/48 overlap, top 5, branch pool 20, English FTS with quoted OR terms, NFC query normalization, equal-weight RRF constant 60, no reranker.
- [Protocol](protocol.json): single pass per query/method, fixed selection rule and latency/cost definitions.
- [Gold](gold/v1.jsonl): 28 query-to-document/version/**chunk** references compiled without inference from P04's frozen section labels. All positive grades are 2; nDCG is valid but does not represent independently judged multi-level relevance.
- [Gold lock](gold/v1.lock.json): binds source labels/questions/corpus, config/protocol, model/parser manifest and canonical-LF Python implementation hash. Each referenced section must resolve to exactly one current compatible chunk; unresolved or multi-chunk ambiguity fails preparation.
- Commit `5e336311a099022db95f5a90d08deacdc4cccd34` froze implementation/config/gold before any benchmark inference. Train/dev were run, then commit `24098104eba8559c5a972dd76a426e29e9f5c93c` froze the [development selection](selection.json) before test inference. No runtime source/config/gold change followed that selection.

Train/dev/test contain 8/8/12 queries, producing **84 query-method predictions** across PostgreSQL lexical, pgvector dense and RRF hybrid. Train and dev each have eight positive queries. Test has eight positive queries and four zero-relevance cases. All 28 queries have identical authorized corpus hashes across their three methods. The corpus is shared knowledge, as in P04's original split policy; this is query-family separation, not independently collected document-domain generalization.

## Measured results

Ranking metrics below use positive queries only; the four test zero-relevance queries are excluded rather than counted as perfect retrieval. Timings use **all** queries in the split, including two denied queries that do no embedding. Hit@k is any relevant chunk, Recall@k is fraction of relevant chunks, MRR@k is truncated reciprocal first-relevant rank, and nDCG@k uses `(2^grade-1)/log2(rank+1)` with ideal-order normalization. Conflict questions have two relevant chunks, so Hit@1 can be 1 while Recall@1 is lower.

| Split | Method | Positive n | Hit@1 | Hit@5 | Recall@5 | MRR@5 | nDCG@5 | Median / p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Train | Lexical | 8 | 0.250 | 0.375 | 0.375 | 0.292 | 0.313 | 15.51 /44.93 |
| Train | Dense | 8 | 0.500 | 1.000 | 1.000 | 0.623 | 0.713 | 43.16 /71.24 |
| Train | Hybrid | 8 | 0.500 | 0.625 | 0.625 | 0.542 | 0.563 | 44.11 /50.10 |
| Dev | Lexical | 8 | 0.500 | 0.625 | 0.625 | 0.563 | 0.579 | 15.61 /35.37 |
| Dev | Dense | 8 | 0.875 | 1.000 | 1.000 | 0.938 | 0.954 | 41.18 /49.11 |
| Dev | Hybrid | 8 | 0.875 | 1.000 | 1.000 | 0.938 | 0.954 | 45.95 /56.51 |
| Test | Lexical | 8 | 0.625 | 0.625 | 0.625 | 0.625 | 0.625 | 15.68 /38.56 |
| Test | Dense | 8 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 45.02 /47.60 |
| Test | Hybrid | 8 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 46.62 /56.48 |

Exact unrounded values and all cutoffs 1/3/5 are in each run's [JSON/CSV](runs/test-v1/metrics.json). [Comparison](comparison.json) includes split and query-language breakdowns, observed paired wins, usage and corpus checks. Query-level raw results and failures are retained:

| Split | Per-query outputs | Metrics CSV | Failures |
| --- | --- | --- | --- |
| Train | [predictions](runs/train-v1/predictions.jsonl) | [CSV](runs/train-v1/metrics.csv) | [failures](runs/train-v1/failures.json) |
| Dev | [predictions](runs/dev-v1/predictions.jsonl) | [CSV](runs/dev-v1/metrics.csv) | [failures](runs/dev-v1/failures.json) |
| Test | [predictions](runs/test-v1/predictions.jsonl) | [CSV](runs/test-v1/metrics.csv) | [failures](runs/test-v1/failures.json) |

## Selection and failure analysis

The preregistered rule chooses highest **dev MRR@3**, then dev Recall@5, then lower observed dev median latency, then method name. Dense and hybrid tie at 0.9375 MRR@3 and 1.0 Recall@5; dense's median was 41.18 ms versus 45.95 ms. Therefore **dense is the selected local baseline candidate** for P07. This is not production approval. Timing differences from eight single-run queries are noisy, and the rule's final tie-break is not evidence of a stable performance advantage. Test was not used for selection or parameter changes.

Observed quality examples are reported without manufacturing a lexical success:

- `qa-a-encoding-ja`: lexical returned no matching chunk; dense ranked the authorized `section:encoding` first. Default PostgreSQL dictionaries do not provide Japanese morphology. An actual SQL probe also shows that the word `在庫` does not match the continuous clause `在庫数は整数です` under `simple` FTS.
- `qa-a-encoding-en`: lexical first ranked an irrelevant intro and found the expected section at rank 3; dense put it first. This is an observed cross-language difference, not proof of general translation quality.
- Across the 24 positive queries, dense has **13 MRR@5 wins**, lexical **0**, and 11 ties. **No lexical quality win was observed.** Lexical had lower latency in these runs; that is reported separately from retrieval quality. A new showcase was not added after test inspection.
- Train mapping queries expose weaknesses: dense retrieves the correct A-English/A-Japanese mapping sections only at ranks 5/4, and hybrid can demote relevant mapping evidence out of top 5. RRF does not guarantee improvement. No test-derived weight/chunk/tokenizer tuning was applied.
- All three paths return zero for the two access-denied test questions, with **zero forbidden hits** across 84 predictions. The two unknown-answer test questions still receive candidates; **retrieval is not an abstention classifier**. P07 must decide whether evidence supports an answer. These counts do not establish answer factuality, safe instruction handling or an end-user authorization boundary.

## Latency and cost boundaries

Median/p95 are client elapsed times, one run per query, local Windows CPU and loopback PostgreSQL. p95 uses linear interpolation at `(n-1)*0.95`; model load (about 1.6–1.8 seconds per split) is recorded separately and excluded. Method order is fixed lexical/dense/hybrid, so warmup/cache/run-order effects exist. This is not load testing or a latency SLA. SQL timings in predictions cover ranking statements; total latency also includes corpus identity lookup, embedding, transaction/audit and Python work.

Measured query embedding usage totals **52 calls /928 valid input tokens**, including E5 prefixes/special tokens and excluding padding, with **$0 provider-billed inference cost**. The two denied questions skip embeddings. The local ONNX model makes no inference API request and no VyceAI/OpenRouter balance is used. CPU electricity/hosting cost is **NOT MEASURED**. Earlier P05 corpus-embedding work and model download are not included as new query-embedding cost. Lexical uses zero embedding tokens/calls. Raw usage is recorded per prediction rather than inferred from a model price table.

## Reproduce and preserve the holdout

Use the clean environment/setup in [ingestion docs](../../docs/ingestion.md), AI PostgreSQL app/curator env, migrated head `0003_lexical_indexes`, and the already downloaded pinned E5 bundle. First ingest P04 via the real P05 corpus CLI if starting a fresh database. Existing run directories are immutable; a repeat with a fresh directory is a replication/regression run, not another unseen test. The designated `test-v1` path refuses overwrite or alternate test output paths.

Original commands, in order:

```powershell
python -m uv run --frozen python -m vmarket_ai.retrieval.evaluate prepare
# Commit implementation/config/protocol/gold.
python -m uv run --frozen --extra local-embeddings python -m vmarket_ai.retrieval.evaluate run --split train --output evals/retrieval/runs/train-v1 --bundle .local/models/multilingual-e5-small
python -m uv run --frozen --extra local-embeddings python -m vmarket_ai.retrieval.evaluate run --split dev --output evals/retrieval/runs/dev-v1 --bundle .local/models/multilingual-e5-small
python -m uv run --frozen python -m vmarket_ai.retrieval.evaluate select --development-run evals/retrieval/runs/dev-v1
# Commit the selection before test inference.
python -m uv run --frozen --extra local-embeddings python -m vmarket_ai.retrieval.evaluate run --split test --output evals/retrieval/runs/test-v1 --bundle .local/models/multilingual-e5-small
python -m uv run --frozen python evals/retrieval/analyze.py
```

`make retrieval-eval-check` recomputes metrics from saved rankings/gold and verifies hashes without loading E5, using a key or contacting PostgreSQL. CI executes this **artifact verification**, not a new real-model benchmark. It refuses a changed comparison artifact. The [test consumption record](test-consumption.json) makes explicit that these 12 queries have now been inspected: later development may use them as regression cases, but P13 needs a fresh independently reviewed frozen set for a new unseen-quality claim. Independent-human-gold and customer-quality gates remain pending.
