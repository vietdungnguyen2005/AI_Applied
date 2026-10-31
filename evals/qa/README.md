# P07 development QA probes

[Cases](cases.jsonl) and [protocol](protocol.json) were committed before first live inference. Four agent-authored development examples cover English/Japanese encoding, unknown tax and conflicting correction deadlines. They are not human gold or an unseen holdout. Expected decisions and literal fact anchors are deterministic proxies only.

The original [raw baseline/RAG run](runs/live-v1/predictions.jsonl) and [summary](runs/live-v1/summary.json) are retained unchanged. It stopped after provider failure. `completed_calls`/usage there count returned ChatResult objects; [ledger reconciliation](../../docs/evidence/P07-ledger-reconciliation.json) also accounts for one settled response with usage but unusable answer content. Do not treat the original summary as total usage.

Later bounded software-validation artifacts preserve those failures:

- [Quote-validator fix confirmation](../../docs/evidence/P07-live-confirmation.json): fresh output still failed validation with 502.
- [Structured-output smoke](../../docs/evidence/P07-structured-live-smoke.json): valid 200 but insufficient response before supplier alias context was supplied.
- [Final vendor/schema smoke](../../docs/evidence/P07-final-live-smoke.json): English/Japanese verified quotes and citation links; unknown-tax provider error, then skip/stop.
- [Real TCP fake-chat demo](../../docs/evidence/P07-fake-http-smoke.json): real PostgreSQL/local E5, fake abstentions and pre-chat conflict guard.
- [Final ledger](../../docs/evidence/P07-live-usage-final.json): eight overall attempts, seven settled requests reporting $0 and one uncertain. No further inference/reset occurred.

Final positives have 2/2 anchor passes and quote-supported answers; the completed prompt-only positive has 0/1. Unequal small denominators, different routed models and changing development revisions prevent a matched causal accuracy comparison. Unknown-tax is a provider error, not correct abstention. Human semantic factual accuracy/citation relevance are NOT RUN. See [partial evaluation summary](../../docs/evidence/P07-evaluation-summary.json).

`python -m vmarket_ai.qa.evaluate --live --output <new-directory>` requires explicit live settings, synthetic corpus and the existing bundle. It refuses overwrite, caps attempts, uses free-only routing and stops on provider errors. Do not invoke it while the real ledger is blocked. CI executes offline/mocked tests and real PostgreSQL plumbing, never this probe or provider keys.
