# P13 — new-question local QA and retrieval measurement

Executed **2026-11-02 17:06 Asia/Bangkok** (10:06 UTC). Before inference, commit
`4cf5b9787c88bd9fbc272bd3409f0a22b29369db` froze eight question inputs, separate
provisional labels, scorer, protocol and dataset hashes. This set uses the same
known synthetic documents and the author had seen prior metrics. It is not an
independently blind, human-labeled, new-document or customer holdout.

The run used real local Java login/profile lookup, signed BFF QA, dedicated
disposable AI/business PostgreSQL and Redis, pinned CPU multilingual E5 and actual
Ollama `qwen3.5:4b-q4_K_M` (model digest/runtime in
[config](../../evals/p13/runs/new-questions-v1/config.json)). The QA path used the
current Java/BFF/Python extractive-answer pipeline. Retrieval additionally ran
lexical/dense/hybrid against identical eligible-corpus hashes for each case. An
empty-evidence service guard is a deliberately limited baseline: it short-circuits
before a model call and does not include Java/BFF HTTP latency.

| Actual recorded result | Outcome |
| --- | --- |
| Data coverage | 8 signed local-QA calls, 8 empty-evidence guard outputs, 24 lexical/dense/hybrid retrieval calls; all 40 rows retained |
| QA provisional decision / answer-anchor / citation proxies | 8/8 decisions; 6/6 answer-anchor and relevant-section matches among answerable questions; 2/2 abstention reasons |
| Retrieval document+section Recall@5 / MRR@5 | Lexical 0.857/0.786; dense 1.000/1.000; hybrid 1.000/1.000, each on seven relevant cases. Unknown case excluded from ranking denominator |
| Negative observation | Lexical returned no hits for Japanese quantity question `q13-05`; dense and hybrid returned the labeled section. P06 had already selected dense; no post-run tuning |
| Proxy limitation | `q13-01` included an extra Japanese approval sentence alongside the correct receipt lifetime; anchor/citation proxies still passed. Independent semantic review is needed |
| Safety / cost | No external inference requested; local provider charge $0; electricity, hardware and hosting not measured. Eleven business-table count/hash snapshots unchanged |

All responses/metrics are based on provisional agent-authored labels; the small
sample and topic overlap make the percentages descriptive only. No confidence
interval, judge score, generalization or human acceptance is claimed. The labeled
data, outputs and questions are now consumed and any repeat is a regression run.

The [raw journal](../../evals/p13/runs/new-questions-v1/raw.jsonl) was flushed
before labels were parsed. The [report](../../evals/p13/runs/new-questions-v1/report.json)
includes every scored row and Java table snapshots; the
[summary](../../evals/p13/runs/new-questions-v1/summary.csv),
[config](../../evals/p13/runs/new-questions-v1/config.json) and
[manifest](../../evals/p13/runs/new-questions-v1/manifest.json) record reproducible
scores, source/model/config identities and file hashes. An offline verifier checks
all 40 case/method identities, journal and Git-freeze hashes, individual scores,
aggregates and CSV. A negative test confirms a missing observation is rejected even
if its journal hash is rewritten. The
[blind review packet](../../evals/p13/new-questions-v1/REVIEW.md) is blank: no
reviewer identity or independent sign-off has been invented.

The owned test containers, Java/BFF/Python processes and Ollama process started for
this run were stopped; the pre-existing user container was left running. No
production deployment, provider-ledger reset or changes to frozen P04/P06 artifacts
occurred. Other required P13 work remains: independently reviewed fresh holdout,
matched prompt-only and reranker comparisons, mapping holdout, tool selection,
security/workflow task metrics and complete cross-domain failure analysis.
