# V-Market AI Operations Copilot — Phase roadmap

Source of requirements: [saved prompt package](implementation-prompts.md). Date: 2026-10-31. Execution is sequential with evidence and acceptance gates. No phase is complete merely because its documentation exists.

Progress update: 2026-11-02 Asia/Bangkok, through P12 UI/signed-source implementation and actual local Java/BFF/PG/E5/Ollama browser acceptance after Docker recovery. P06's test split is now consumed; later phases must distinguish regression reuse from fresh unseen evaluation.

Implementation owner: coding agent; acceptance owner: repository owner. Real stakeholder feedback and human labels must be supplied or explicitly labeled simulation/developer review. Fake provider tests prove deterministic plumbing, never real model quality.

| Phase | Dependency | Deliverable / exit gate | Owner | Status |
| --- | --- | --- | --- | --- |
| P00 | Existing repos | Source audit, actual baseline logs, risks and concrete integration plan | Agent / owner review | Accepted by owner instruction to continue; dependency audit FAIL remains open |
| P01 | Owner acceptance of P00 | Fictional discovery, FR/NFR, J1–J5, negative acceptance cases | Agent / owner | Documentation delivered and checked; no real discovery/UAT or AI implementation claimed; see evidence/P01.md |
| P02 | P01 | ADRs, schemas, identity protocol, threat review | Agent / owner | Design delivered; contract examples validated; runtime auth/security gates pending; see evidence/P02.md |
| P03 | P02 | Fake-default FastAPI, migrations, CI, lint/types/tests/health | Agent | Local foundation verified: lint/types, 45 offline tests +1 PostgreSQL test, contracts, clean environment and Docker smoke; see evidence/P03.md. Remote CI status is separate |
| P04 | P03 + verified profile contract | Synthetic fixtures, byte hashes, provenance, separated gold splits | Agent / human review | Technical dataset/QA delivered; independent human-curated gold PARTIAL/pending; ingestion plumbing may proceed but quality claims remain gated; see evidence/P04.md |
| P05 | P03–P04 | Actual parsers, chunking, embeddings, versions, ACL | Agent | Internal pipeline/CLI implemented and locally checked; real CPU E5/pgvector, fake CI, transactional version/delete and SQL scope tests; signed HTTP identity remains P09; see evidence/P05.md |
| P06 | P05 | Lexical/dense/hybrid implementations and measured retrieval eval | Agent | Technical implementation and real local-model benchmark delivered; dev-selected dense config frozen before test, all 84 outputs retained; metrics provisional, independent human review pending; see evidence/P06.md |
| P07 | P06 | Grounded QA, citations, abstention and provider negatives | Agent | Opt-in extractive API/citation checks and English/Japanese live positives verified; balanced live comparison PARTIAL, human review pending, real live ledger blocked on one uncertain outcome; see evidence/P07.md |
| P08 | P04–P07 | Strict draft mapping and rule-only comparison | Agent | Standalone draft API, original-byte storage, strict local/rule suggestions and 228 retained known-case outputs verified; rules selected by measured comparison, human/unseen/business-quality gates pending; see evidence/P08.md |
| P09 | P02,P03,P07,P08 | Mock tools and feature-OFF real BFF gateway with per-action auth tests | Agent / owner | Technical standalone/integrated local read-only delivery verified with real disposable OPERATOR/auth and unchanged business snapshots; Project2 local commit + reviewable patch, flags OFF, no deploy; quality/human gates pending; see evidence/P09.md |
| P10 | P08–P09 | Explicit human profile/preview/confirm handoff, DB invariant tests | Agent / owner | Technical implementation verified: signed current-profile draft, explicit edit/create inactive/activate, real CP932/UTF-8 browser journeys, lost202 recovery, completed replay and rejection DB invariants; independent human/UAT/quality gates pending; see evidence/P10b.md |
| P11 | P09–P10 | Durable bounded state and actual restart/resume tests | Agent | Technical delivery verified: owner-bound SQL checkpoints, revision/lease fencing, explicit uncertain-read recovery, current authorization, TTL/owner retention, real process restarts and no redispatch; see evidence/P11.md. UI remains P12; human/model-quality gates pending |
| P12 | P07–P11 | Flagged operator panel, browser QA and manual fallback | Agent | Technical delivery verified default-OFF: grounded QA/current source dialog, bounded read-only conversation, live tool observations and human handoff; mocked browser faults and actual Java/BFF/PG/E5/Ollama browser checks passed. Revoked-source404 and unchanged 11 business tables verified. See evidence/P12.md; independent human/model-quality acceptance pending |
| P13 | P04–P12 | Frozen held-out metrics, ablations, raw outputs, failure analysis | Agent / human review | Technical measurement DELIVERED: all retained/provisional metrics, local mapping test and matched QA, rerank comparison, routing/gate results, failure remediation. Human quality acceptance PARTIAL; original mapping test now consumed. Owner requested continuation to P14 with review/task-quality limits carried forward; see evidence/P13.md |
| P14 | P09–P13 | Security negatives, both repo regressions, dependency remediation | Agent / owner | IN PROGRESS: official 2026 threat inventory opened; fresh npm audit fails with 17 moderate/2 high entries. Reachability, fixes and both-repo regression review pending; see evidence/security-review.md. R08 and independent quality acceptance remain open |
| P15 | P14 | Reproducible standalone/integrated local modes, budgets, CI/drills | Agent | NOT STARTED |
| P16 | P13–P15 | UAT, English delivery/interview evidence and honest final gate | Agent / owner | NOT STARTED |

## Owner-requested local inference extension

After P07, the owner requested community/documentation/hardware research and approved implementing local chat before P08. [Local inference](local-llm.md) adds Ollama with real 4B/9B development probes; [evidence](evidence/LOCAL.md). This does not complete P08 mapping or resolve P07's uncertain cloud charge/human evaluation gates.

## Persistent execution rules

- Never request that the owner paste the individual prompts again; use this saved package and roadmap.
- Advance only when prerequisites and relevant acceptance criteria are verified; carry unresolved limitations forward explicitly.
- For each phase, write `docs/evidence/Pxx.md`, raw redacted outputs, artifact hashes, before/after SHA/status and actual test results. Keep a focused branch/change set and preserve manual ops compatibility.
- No production deploy, paid resources, external data disclosure, business mutation by an AI tool or automatic privilege expansion. Existing explicit authorization to push AI_Applied applies to reviewable source branches, not production deployment or Project2 rollout.
- The supplied package explicitly gates P01 on owner acceptance of P00. The owner can change that review cadence with an explicit instruction; until then preserve the gate.
