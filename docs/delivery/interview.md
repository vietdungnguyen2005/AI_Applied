# Interview preparation, FAQ and truthful portfolio wording

Answers describe this synthetic local project. Use the linked source/evidence,
not a claim of a production customer or independently validated model accuracy.

## 25 technical questions and concise answers

1. **What is the business boundary?** Python proposes reads/drafts; Java alone
   owns authorization and business mutation. See technical handoff and P10b.
2. **Why a BFF?** It holds the browser session/CSRF and fixed Java transports,
   derives scopes and signs bounded AI context without giving Python those secrets.
3. **How is caller identity verified?** Ed25519 context binds actor/action/body,
   nonce/expiry/run/step; server validates it before protected processing.
4. **How do you prevent replay?** Atomic stored nonce plus owner/revision/lease
   fencing; real PG concurrency assertions and durable recovery tests.
5. **Can the model select an arbitrary URL or HTTP method?** No. A closed intent
   union compiles arguments into server-owned read-only transport.
6. **What security defect did evaluation uncover?** History substring matching
   admitted metadata/document UUIDs as jobs. P14 now accepts only explicit user
   UUID tokens or typed observed business job fields; seven cases cover the fix.
7. **Does known job ID mean authorized?** No. Java/BFF reauthorize every actual
   read and the server limits supplier scope; provenance is an additional gate.
8. **How is source access enforced?** SQL grant/version/expiry filtering occurs
   before ranking/limits; current source access is checked again before release.
9. **Why exact quotes?** The model selects bounded full source sentences; quote
   and citation validation constrain free-form fabrication. Relevance still needs review.
10. **What was a real QA failure?** Mixed English/Japanese sentence segmentation
    rejected a valid quote. A failing test and raw-output replay drove a focused fix;
    original6/8 score was preserved.
11. **How are conflicts handled?** Production has a conservative overlapping-source
    guard. A generic generator-only conflict result violated the claims invariant;
    it is retained as invalid, not silently counted correct.
12. **What embedding pipeline is used?** Pinned multilingual E5 small CPU bundle,
    versioned fingerprint, pgvector, 320-character chunks/48 overlap and preserved locators.
13. **Why dense rather than hybrid?** Development measurements selected dense;
    known test results were not used to retune. Lexical missed Japanese cases.
14. **Did reranking improve results?** No. Exploratory bigram rerank degraded dev
    MRR@5 from0.9375 to0.8375 and left test unchanged. Default stays none.
15. **How was retrieval ablated?** Lexical/dense/hybrid use matched authorized
    corpora; generator diagnostic changes only source array with fixed prompt/schema/model.
16. **What mapping quality was measured?** On12 original test inputs, exact target
    labels exist for10: rules0/10, AI2/10. Labels are provisional; abstention remains a miss.
17. **What does a passing fake test prove?** Plumbing and deterministic controls,
    not semantic model quality or generalization.
18. **How are originals protected?** Decode only under declared encoding; preserve
    immutable bytes/SHA and exact headers; Java receipt/profile validation remains authoritative.
19. **What happens after a lost202?** It is pending/unknown; inspect the same job,
    do not blindly confirm again. Fresh browser recovery and replay invariants passed.
20. **How do runs survive restart?** AI PG stores owner-bound checkpoints with
    revision/lease fencing. Interrupted reads become OUTCOME_UNKNOWN, requiring explicit recovery.
21. **How is external cost bounded?** Fake default, finite opt-in live budgets,
    free-price preflight and ledger reservations. Unknown usage blocks further live calls.
22. **Can local model traffic become cloud traffic?** Loopback Ollama adapter
    rejects remote model metadata/redirects and never pulls/falls back automatically.
23. **What did operations testing find?** DB/DNS readiness could outlive the client
    budget. One in-flight probe and a one-second response budget now fail503 promptly.
24. **What was verified from a clean checkout?** Locked offline install, migrate,
    fake-check, PG-enabled tests, type/contract checks. Exact counts and source SHA are in P15/P16 evidence.
25. **What remains before production?** Independent gold/UAT, quality gates,
    owner review, deployed security/retention/incident ownership and actual capacity evidence.

## Ten customer questions to ask in real discovery

1. Which supplier procedures are authoritative, and who resolves conflicts?
2. Which original encodings/headers and maximum file sizes must be supported?
3. Who may view each document and perform profile/preview/confirm actions?
4. What errors are most costly: wrong mapping, over-refusal or delayed import?
5. What human review steps are mandatory even when a model is confident?
6. How do you handle lost responses, pending jobs and uncertain stock freshness today?
7. What labeled examples and independent reviewers can you provide for acceptance?
8. What data retention, key handling and network/deployment policies apply?
9. Who owns incidents, rollback and manual fallback during service/model outages?
10. What evidence, quality threshold and observed human outcome would justify a pilot?

These questions have not been answered by a real client in this exercise. Do not
invent customer answers from the simulated discovery transcript.

## CV bullets grounded in evidence

- **Applied AI:** Built local multilingual retrieval, extractive cited QA and
  schema-constrained mapping for synthetic supplier workflows; preserved raw
  comparisons, negative rerank results and low mapping accuracy to gate automation.
- **AI Solutions:** Implemented a signed Next/Java/Python boundary, restricted
  read tools, immutable-byte/profile binding and owner-fenced durable runs;
  verified local authorization, restart and manual-fallback behavior.
- **FDE:** Delivered a clearly synthetic customer discovery/architecture/demo/
  runbook/evidence pack and a clean-checkout reviewer path; separated automated
  engineering acceptance from unavailable real-client UAT and ROI.

Do not say “served a paid retailer,” “deployed production AI,” “100% accurate,”
“human-approved,” or claim a percentage productivity increase. If citing numeric
test/eval counts, name the exact phase, dataset, denominator and local/mock scope.

## Review summaries for the two repositories

**AI_Applied:** Adds local operations verification, explicit fake signed-container
configuration with no unsigned route bypass, bounded single-flight readiness,
health/eval metadata scripts and handoff evidence. Existing direct semantic
mode stays loopback; original paid-provider block is preserved. Tests cover the
configuration boundary, actual Docker outage/restart and clean PG-enabled suite.

**Project2 local patch:** Updates Wrangler/body-parser/undici and pins patched
glob/minimatch. Final audit0, frontend124/backend115 tests and Next/Worker builds
pass. Transitive major overrides need compatibility review on future upgrades.
Original checkout remains unchanged; cumulative P14-final patch applies to P12
base998c2eb and reproduces local commit39fbf11. No remote push/merge/deployment.
