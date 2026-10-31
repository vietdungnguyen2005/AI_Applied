# P00 — Skills and evidence gaps

Existing Project2 evidence belongs to Project2; it cannot be attributed to the future AI service. All rows below describe remaining work, not delivered capability.

| Skill | Deliverable / phase | Evidence required | Current status |
| --- | --- | --- | --- |
| Customer discovery / FDE | P01 fictional retailer requirements, journeys J1–J5 and acceptance IDs | Clearly simulated discovery, Given/When/Then and rollback | Not started |
| Architecture / AI Solutions | P02 threat model, schemas, trust-boundary ADR | Source-derived contracts and review checklist | P00 plan only |
| Python service | P03 FastAPI, settings, CI, fake providers, own DB | Clean install, lint/types/tests/health | Not started |
| Data engineering | P04 synthetic CP932/UTF-8 fixtures and labels | Hashes, exact-byte checks, provenance, frozen splits | Not started |
| Ingestion / embeddings | P05 document parsing, versioning, ACL | Parser negatives, idempotency, access denial | Not started |
| Retrieval | P06 lexical/dense/hybrid and reranking decision | Query-level Recall/MRR/latency, actual backend execution | Not started |
| Grounded generation | P07 validated citations and abstention | Gold QA, conflicting/unknown policy cases, opt-in provider evidence | Not started |
| Structured extraction | P08 mapping proposals | Rule baseline, exact mapping metrics and invalid/abstain rates | Not started |
| Tool calling / auth | P09 bounded intents and BFF gateway | Real local operator/guest/revoked-role tests; no secret propagation | Not started |
| Human control | P10 existing profile/preview/confirm handoff | Original bytes, expired/tampered receipt, 202 pending and DB rejection assertions | Not started |
| Reliability | P11 state machine / durable checkpoints | Actual restart/resume/expiry fault evidence | Not started |
| UX | P12 feature-flagged operator panel | Responsive/keyboard/browser QA, manual fallback | Not started |
| Evaluation | P13 frozen held-out harness and ablations | SHA/config/raw predictions/metrics/failure analysis | Not started |
| Security | P14 threat tests and dependency audit | Denial matrix, regressions, residual-risk assessment | Existing dependency audit failing |
| Operations | P15 local modes, budgets, CI and runbooks | Clean-install/recovery drills and measured load data | Not started |
| Delivery / interviews | P16 UAT and honest portfolio pack | Reproducible reviewer path, real results only | Not started |

The existing API probe establishes provider connectivity only, not model quality, RAG correctness or product readiness.
