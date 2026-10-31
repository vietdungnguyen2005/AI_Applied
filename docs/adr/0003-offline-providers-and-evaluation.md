# ADR 0003 — Fake default, real retrieval evidence and bounded live spend

Date: 2026-10-31. Status: accepted design, measurements pending.

Decision: deterministic fake chat/embeddings/tool fixtures support offline CI. Real lexical retrieval and pgvector query paths will be exercised against a separate AI database. Fake dense embeddings test vector plumbing only; semantic retrieval/model quality must be labeled and measured separately. Compare lexical, dense, RRF hybrid and rule-only mapping on fixed held-out synthetic cases; a reranker is claimed only if an actual separate scoring stage executes.

Live providers are optional server config, absent from browser input. Default live allowance is zero. Require finite configured request/day USD budgets, a model price manifest and known worst-case token limits before any call; reserve and account atomically, fail closed on unknown prices/uncertain charges. No automatic paid fallback or blind inference retry. Existing free provider connectivity does not guarantee embeddings, structured output, future availability or free usage under every configuration.

Use a simple controller before adding LangGraph; revisit P11 only if durable recovery requirements justify framework cost. No model training/fine-tuning or multi-agent system is required for the initial scope.

Consequences: offline demos cannot establish real LLM quality. Unknown provider pricing disables live use until verified. Real quality experiments must record provider/model/prompt/data/code/version and measured cost/latency; no external call is authorized by this ADR itself. [P01 metric protocol](../fde/success-metrics.md) defines the quality targets and honest review limitations.
