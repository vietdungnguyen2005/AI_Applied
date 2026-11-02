# P13 — evaluation progress: retained-run regression report

This is a **first increment**, not completion of P13 and not a fresh held-out
quality evaluation. It re-scores 320 previously retained synthetic predictions:
84 retrieval, 228 mapping and eight partial QA rows. It does not invoke a model,
provider, database, Java, or network and does not spend provider balance.
The P06 retrieval test is already consumed and inspected; all P08 mapping runs
exclude the 12 P04 mapping test inputs. The four P07 QA cases are known development
probes. Independent human review of all existing labels remains pending.

Run from a **clean committed checkout**:

```powershell
python -m uv run --frozen python -m vmarket_ai.evaluation.regression
# Or: make p13-regression
```

Each execution creates a fresh ignored `.local/p13-regression-<UUID>` directory.
`--output <fresh-path>` selects another new directory; existing results are never
overwritten. First the P06/P08 offline verifiers check the frozen release, original
bytes, implementation/config hashes and prior summaries. The new runner then
recomputes retrieval ranking scores from actual chunk IDs and provisional labels,
and mapping exact matches from actual projected assignments and provisional
labels. It writes `config.json` (source commit, source/input SHA-256, time and
limitations), `predictions.jsonl` (sanitized per-case predictions and scores),
`summary.csv` (metric, denominator and value), and `manifest.json` (file hashes).
The original predictions and their own model/runtime/config metadata are retained
unchanged under [retrieval](../retrieval/README.md), [mapping](../mapping/README.md)
and [QA](../qa/README.md). The sanitized QA rows omit raw model text; the original
synthetic development responses remain in their original artifacts.

`make p13-check` verifies the checked-in report's manifest, every recorded input
hash and the historical implementation Git blob without rerunning model inference.
Passing `--compare <fresh-output>` additionally checks regenerated predictions and
summary byte-for-byte. Both the regression and comparison run in CI.

The [portable recorded run](runs/retrospective-v2/manifest.json) was produced from
clean source commit `48bdde0` before that report was added. Compare summary/prediction
bytes for reproducibility; `config.json` and its manifest hash differ for a new
run because timestamp and source commit are recorded, not silently held constant.
Git-managed evaluation text and source files use canonical LF for input hashes;
frozen `data/v1` files retain exact original bytes. The earlier
[v1 report](runs/retrospective-v1/manifest.json) remains as historical evidence:
its recorded raw Windows CRLF hashes did not verify on Linux. The v2 predictions
and summary are byte-identical to v1; only provenance/hash handling changed.

## Dataset identity and duplicates

The original [data release lock](../../data/releases/v1.lock.json) and
[retrieval gold lock](../retrieval/gold/v1.lock.json) contain SHA-256 input and
provenance identities; the generated config records hashes of all input run files,
their manifests/configs and labels. Synthetic mapping has 8 train, 6 dev, 12 test
and 25 regression inputs. Two exact-byte duplicate groups are intentionally within
regression only; neither crosses partitions. Retrieval has 8 train, 8 dev and 12
test queries; eight identical-question pairs occur within train or dev with different
supplier scopes, none crosses partitions. Documents are shared across query splits,
so query-family separation does not demonstrate a new document domain. These
checks cover exact bytes/questions, not paraphrase or semantic-near-duplicate review.

## Measured observations and failure analysis

- Consumed retrieval test: lexical Recall@5/MRR@5 **0.625/0.625**, dense and
  hybrid **1.0/1.0**, each with eight relevant queries; the full 12 include four
  zero-relevance queries excluded from those ranking averages. All 36 method/query
  rows report zero forbidden hits. This is a small known regression set and is
  not an HTTP authorization rejection rate or a new unseen-quality estimate.
- Known mapping cases: rule **20/26**, 4B v2 **19/26**, 9B **16/26**, and the
  initial 4B prompt **3/26** exact labeled matches. The 4B prompt revision was
  motivated by a measured development failure; this is not an independent test
  or proof that prompt wording alone caused the difference. A reranker ablation,
  matched no-retrieval QA comparison, deterministic-vs-LLM tool routing, and
  fresh held-out metrics remain **NOT RUN**.
- The old aggregate name `negative_gold_cases_with_assignments` treated all
  mapping rows without a mapping target as if they were negatives. Inspection
  shows the local-v2 rule case `reg-b-missing-header` instead produced partial
  assignments with `needs_review` while its provisional expected status is
  `input_error`. A missing target is not itself a negative correctness label.
  The new report calls this **unlabeled mapping with assignments**, excludes it
  from exact-match denominators and preserves its actual status/assignments for
  review. It does not change mapping behavior or claim the case is safe/unsafe.
- P07 retrieval QA recorded 502 and 503 failures and two skipped cases: **0/4
  valid responses**, so decision accuracy is **undefined**, not 0% semantic
  accuracy. Prompt-only completed only **1/4**, with 0/1 matching the provisional
  decision. The old summary's `decision_correct: 0` did not make that denominator
  clear. The new report separates valid-response coverage, service failures and
  accuracy among valid responses; a zero denominator is blank/null. The unequal
  and partial samples do not support a causal RAG comparison.

Latency is the historical client/request measurement with linear-interpolated p95;
warmup is excluded where the source experiment excluded it. Local provider-billed
query embedding cost is zero; power, equipment and hosting costs were not measured.
No confidence interval or judge score is reported for these tiny non-independent
development samples. The prior live-provider ledger remains blocked after an
uncertain call and was not touched by this offline analysis.

## P13 work still required

An [additional question set](new-questions-v1/inputs.jsonl) is preregistered for
local QA and lexical/dense/hybrid retrieval. Its separately stored provisional
[labels](new-questions-v1/labels.jsonl), [protocol](new-questions-v1/protocol.json)
and [lock](new-questions-v1/lock.json) are frozen before the first model run. The
lock's `inference_has_occurred: false` records the freeze-time state and is not
updated after execution. `python -m vmarket_ai.evaluation.new_questions` checks
the release, IDs, source references and exact normalized duplicate questions.
All eight questions are new to this experiment, but their author knew previous
results, the SOP documents are shared and some topics overlap earlier cases. This
is **not** an independently blind or human-reviewed new-domain holdout.

### Executed local QA and retrieval run

On 2026-11-02 17:06 Asia/Bangkok (10:06 UTC), the frozen questions were run once
using actual Java authentication/profile selection, signed BFF QA, separate AI
PostgreSQL, pinned CPU multilingual E5 and local `qwen3.5:4b-q4_K_M`. The
preregistration commit is `4cf5b9787c88bd9fbc272bd3409f0a22b29369db`. The
[immutable run package](runs/new-questions-v1/manifest.json) contains the complete
[40 raw observations](runs/new-questions-v1/raw.jsonl),
[per-case scored report](runs/new-questions-v1/report.json),
[summary CSV](runs/new-questions-v1/summary.csv), model/config/input hashes and a
blank independent-review template. All eight QA and all 24 retrieval calls are
represented, as are eight empty-evidence guard outputs. No case was retried or
removed. `PASS` in the run means collection finished; the numbers below determine
individual outcomes.

| Measurement | Result | Denominator and limits |
| --- | --- | --- |
| Signed dense/local QA decision proxy | 8/8 | Six answerable, one unknown and one conflicting-source case; provisional agent labels |
| Answer anchor / relevant citation proxies | 6/6 each | Answerable cases only; not human semantic or citation-quality review |
| Abstention reason proxy | 2/2 | One unknown and one conflicting-source case |
| Lexical Recall@5 / MRR@5 | 0.857 / 0.786 | Seven cases with at least one provisional relevant document/section |
| Dense Recall@5 / MRR@5 | 1.000 / 1.000 | Same seven cases and authorized corpus |
| Hybrid Recall@5 / MRR@5 | 1.000 / 1.000 | Same seven cases and authorized corpus |
| Empty-evidence guard decision proxy | 2/8 | The guard returns before invoking a model; it is not a matched prompt-only LLM baseline |

The unanswerable case has no relevant section and is excluded from ranking averages,
not treated as a perfect retrieval. Retrieval is scored at **document + section**
level after deduplicating sections within the returned top five chunks; the
conflict case has two relevant sections. Each retrieval method used the same
eligible-corpus hash for each case. Local retrieval median/p95 wall times in ms
were lexical 9.52/31.47, dense 20.29/25.19 and hybrid 24.58/32.90, with eight
sequential requests per method; warmup and process startup are excluded. The
signed Java/BFF QA median/p95 were 2083/5095 ms. Guard timing is a direct service
call without HTTP/auth and is **not comparable** to BFF QA timing. E5 recorded
0/8/8 query embedding calls for lexical/dense/hybrid, respectively. The local
provider charge was $0 and no external inference was requested; electricity,
hardware and hosting cost were not measured. These small, ordered single-run
timings are not an SLA or a basis for a confidence interval.

The lexical retriever returned no hits for Japanese quantity question `q13-05`;
dense and hybrid both returned the labeled mapping section. Dense was already
selected using the P06 development rule before this run, and no post-run tuning
was performed. This is consistent with the known tokenizer limitation on another
question over the same corpus; it does not prove general Japanese retrieval performance.
In `q13-01` Qwen included an extra Japanese sentence about approval along with the
correct receipt lifetime. Both automated anchor/source proxies passed; whether the
extra sentence is relevant must be decided in independent semantic review. This is
an observed limitation of the proxy, not grounds to claim 100% factual quality.
The [blind review instructions](new-questions-v1/REVIEW.md) and blank template
provide the review step; nobody has completed it yet.

The 12 previously unconsumed P04 mapping test inputs now also have a separate
[blind, byte-preserving mapping review packet](mapping-review-v1/README.md). It
contains no provisional mappings or model outputs. Review is pending; preparing
the packet did not run inference on those inputs. The original test cases remain
synthetic and agent-authored, not independent customer data.

To reproduce operationally, start the existing local Ollama 4B model and Docker,
prepare the Project2 production build/JAR, then run in a clean committed checkout:

```powershell
python -m uv run --frozen --offline --extra local-embeddings python tools/p13_new_questions.py --project2 D:/CV/Project2 --output .local/p13-new-repeat.json
```

This uses fresh disposable databases/Redis and records every response in an ignored
journal before labels are parsed. A repeat is a **regression**, since these questions
and results have now been inspected. The output report records the journal filename;
package it into a fresh directory with `tools/p13_new_pack.py --report <report>
--journal <journal> --output <fresh-directory>`. Verify the committed run without
any inference using `python -m uv run --frozen python tools/p13_new_verify.py
--artifact evals/p13/runs/new-questions-v1`. It recomputes per-case scores and the
CSV from all 40 journaled observations, verifies the frozen inputs and scoring code
at the preregistration commit, and validates artifact hashes.

Design and freeze a **new** independent held-out release and separate model input
from labels; record exact and near-duplicate review and independent human label
review. The release must cover answer/source/abstention/conflict, retrieval,
mapping and abstention, allowed tools/arguments and prohibited actions, document
and tool authorization, and handoff/stale-approval/unknown-outcome workflows.
Then run the preregistered matched ablations, measure tool correctness, denial and
task success, retain sanitized outputs/latency/cost, and perform failure-driven
remediation without using held-out answers for tuning. P13 remains open until
those runs and reviews are actually complete.
