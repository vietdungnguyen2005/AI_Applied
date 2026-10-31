# V-Market AI Operations Copilot — Phase roadmap

Source of requirements: [saved prompt package](implementation-prompts.md). Date: 2026-10-31. Execution is sequential with evidence and acceptance gates. No phase is complete merely because its documentation exists.

Implementation owner: coding agent; acceptance owner: repository owner. Real stakeholder feedback and human labels must be supplied or explicitly labeled simulation/developer review. Fake provider tests prove deterministic plumbing, never real model quality.

| Phase | Dependency | Deliverable / exit gate | Owner | Status |
| --- | --- | --- | --- | --- |
| P00 | Existing repos | Source audit, actual baseline logs, risks and concrete integration plan | Agent / owner review | Audit delivered; awaiting owner acceptance; dependency audit FAIL recorded |
| P01 | Owner acceptance of P00 | Fictional discovery, FR/NFR, J1–J5, negative acceptance cases | Agent / owner | NOT STARTED |
| P02 | P01 | ADRs, schemas, identity protocol, threat review | Agent / owner | NOT STARTED |
| P03 | P02 | Fake-default FastAPI, migrations, CI, lint/types/tests/health | Agent | NOT STARTED |
| P04 | P03 + verified profile contract | Synthetic fixtures, byte hashes, provenance, separated gold splits | Agent / human review | NOT STARTED |
| P05 | P03–P04 | Actual parsers, chunking, embeddings, versions, ACL | Agent | NOT STARTED |
| P06 | P05 | Lexical/dense/hybrid implementations and measured retrieval eval | Agent | NOT STARTED |
| P07 | P06 | Grounded QA, citations, abstention and provider negatives | Agent | NOT STARTED |
| P08 | P04–P07 | Strict draft mapping and rule-only comparison | Agent | NOT STARTED |
| P09 | P02,P03,P07,P08 | Mock tools and feature-OFF real BFF gateway with per-action auth tests | Agent / owner | NOT STARTED |
| P10 | P08–P09 | Explicit human profile/preview/confirm handoff, DB invariant tests | Agent / owner | NOT STARTED |
| P11 | P09–P10 | Durable bounded state and actual restart/resume tests | Agent | NOT STARTED |
| P12 | P07–P11 | Flagged operator panel, browser QA and manual fallback | Agent | NOT STARTED |
| P13 | P04–P12 | Frozen held-out metrics, ablations, raw outputs, failure analysis | Agent / human review | NOT STARTED |
| P14 | P09–P13 | Security negatives, both repo regressions, dependency remediation | Agent / owner | NOT STARTED; R08 open |
| P15 | P14 | Reproducible standalone/integrated local modes, budgets, CI/drills | Agent | NOT STARTED |
| P16 | P13–P15 | UAT, English delivery/interview evidence and honest final gate | Agent / owner | NOT STARTED |

## Persistent execution rules

- Never request that the owner paste the individual prompts again; use this saved package and roadmap.
- Advance only when prerequisites and relevant acceptance criteria are verified; carry unresolved limitations forward explicitly.
- For each phase, write `docs/evidence/Pxx.md`, raw redacted outputs, artifact hashes, before/after SHA/status and actual test results. Keep a focused branch/change set and preserve manual ops compatibility.
- No production deploy, paid resources, external data disclosure, business mutation by an AI tool or automatic privilege expansion. Existing explicit authorization to push AI_Applied applies to reviewable source branches, not production deployment or Project2 rollout.
- The supplied package explicitly gates P01 on owner acceptance of P00. The owner can change that review cadence with an explicit instruction; until then preserve the gate.
