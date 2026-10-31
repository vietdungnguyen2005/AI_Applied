# Discovery questionnaire — proposed, not conducted

Audience: fictional Japanese retailer and synthetic suppliers A/B. Use these questions in a real future discovery session; no participant answers have been collected. Record each answer with owner, date, evidence, confidence and whether it is a preference or existing system fact.

## Business operator

1. Walk through your last supplier file from receipt to inspection. Which decisions required judgment?
2. Which columns change most often, and who confirms their business meaning?
3. How do you establish that an on-hand quantity is fresh and belongs to the selected supplier?
4. Which wrong mapping is most harmful? When should the assistant abstain instead of guessing?
5. What must be visible before you accept a draft: original header, target, sample, source/version or uncertainty?
6. What do you do when confirmation returns 202, times out or loses its response?
7. Which SOP questions recur, and which require an explicit policy owner?
8. Can we measure the same synthetic cases manually and with assistance, without mixing practice and held-out cases?

## Supplier contact

1. What are the declared encoding, header spelling, delimiter and newline conventions?
2. Who announces changes and assigns file versions? Are unchanged filenames ever reused?
3. Is a quantity a snapshot or a movement, and what is its effective time?
4. How are duplicates, unknown SKUs and corrections communicated?
5. Can you provide a redistribution-safe synthetic example and a glossary of ambiguous headers?
6. Who owns English/Japanese SOP translations and resolves a conflicting translation?

## Security and data owner

1. Which current roles may inspect imports and read each knowledge collection?
2. Is supplier scoping a UI filter or an actual authorization rule? What must never be described as tenant isolation?
3. What data may be sent to an external model, under what budget and retention conditions?
4. Who approves document ingestion, retention, deletion and policy version changes?
5. What should happen when a user is disabled between two tool calls or while a run is paused?
6. Which fields must be removed from tool outputs, logs and model context?
7. Which actions must always stay in the existing human-operated workflow?

## Engineering and operations

1. Which backend revision is actually deployed, and how is that attested?
2. Which GET contracts can be safely reused, with what bounds and missing-resource status?
3. How do session refresh, CSRF, server trust, preview receipts and import fencing interact?
4. What request, response, step, deadline and external-spend budgets can be enforced?
5. What is the fallback when the AI service, provider, index or Java API is unavailable?
6. What records prove that rejected AI requests caused no business write?
7. Which baseline regressions and dependency advisories block integration/release?
8. Who reviews gold labels, signs off UAT, owns runbooks and approves any future deployment?

Close the session by replaying an example of success, abstention, unauthorized access and unknown import outcome. Ask each participant to correct assumptions. A simulated answer cannot count as that validation.
