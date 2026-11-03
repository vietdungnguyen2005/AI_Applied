# Same-model cloud mapping diagnostics

These are small synthetic developer-authored diagnostics, not independent supplier
acceptance, human UAT or measured onboarding-time savings. They do not replace the
historical P13 local 4B mapping result. No development case is subsequently called
an unseen holdout.

Sequence:

1. `pilot-v1/cases.json` and its hash were committed before prompt changes. The
   original deployed adapter (`a938163`, Worker `b1f79f3d-6f29-472f-9efe-1084557e0aed`)
   was compared with structured-context v2 (`e839afb`, temporary candidate Worker
   `6da4fe45-699a-4a76-bfaa-53dd59f9c6ac`). Both use Qwen3 30B A3B, temperature 0
   and 512 output tokens. V2 failed the release gate: fewer wrong suggestions but
   three newly omitted supported mappings. Its observations and report are retained.
2. `refinement-v1` explicitly reuses consumed development cases and baseline
   observations. V3 removes absent old-profile bindings from model evidence,
   clarifies proposal versus approval, and rejects bare vendor/supplier identity
   as an unapproved product key. No labels or previous predictions enter runtime
   context. This is development refinement, not a new evaluation sample.
3. `followup-v1` froze six additional cases. Its first baseline request failed at
   the Node transport before a service response. That failure and aborted outcome
   remain recorded. V3 still omitted two supported pairs on development data.
4. Runtime `2ef2d20` adds conservative typed candidates for unique explicit
   physical-stock and display-name columns before inference. This rule change was
   committed before any successful response on the six follow-up cases.
   `verification-v1` attempted repeat collection but also stopped on its first
   Node connection failure; the original observation remains recorded.
5. `transport-verification-v1` repeats the same six cases using curl after a
   successful curl health check. Runtime, model, labels and scoring are unchanged.
   Its inputs and transport choice were committed before collection. This is
   repeated synthetic diagnostic collection, not independent validation. There
   are no automatic retries, and transport-aborted trials are never erased.

The final six-case collection passes the engineering gate: exact cases 3/6 →
6/6, incorrect proposed pairs 2 → 0, missing supported pairs 2 → 0, complete
mappings 3/3 → 3/3. Baseline returned HTTP 502 on `new-money` (retained without
retry); candidate returned 200 for all six. The exact-case gain therefore includes
recovery of that failed response, not only semantic quality on successful calls.
The final runtime has not been recollected on all 12 development cases; do not
attribute earlier development scores to it.

Reported dimensions: complete file mappings, partially unresolvable cases,
correct/incorrect proposed field pairs, and missing supported pairs. The
`required_pair_changes` count is a comparison against provisional labels, **not
observed user edits or time saved**. Model-attempt counts are inferred from the
successful response's model-draft branch, not billing or neuron measurements.

The promotion gate requires all cases to return 200, no increase in incorrect
proposed pairs, and no decrease in exact complete-file mappings versus baseline.
It is an engineering gate for these cases, not a calibrated quality guarantee.

Recompute scores offline from retained inputs and service responses:

```powershell
python tools/cloud_mapping_pilot.py --check
python tools/cloud_mapping_pilot.py --directory evals/cloud-mapping/refinement-v1 --check
python tools/cloud_mapping_pilot.py --directory evals/cloud-mapping/transport-verification-v1 --check
```

Live collection requires an owner-controlled BFF Ed25519 signing key in the
process environment. Never put it in a script, shell argument, output artifact or
Git. Preserve the original deployed baseline until both arms have been collected.
Verify Workers Free and available quota first; both Workers share the real D1
60-attempt/day budget. The runner uses a single synthetic actor, waits between
batches, and does not retry recorded failures. A separate CLI invocation after a
failure resumes only cases that have no observation; it does not rerun the failure.

```powershell
# Set AI_SIGNING_KID and AI_SIGNING_KEY_PKCS8_BASE64 securely outside command history.
node cloudflare/tools/run-mapping-pilot.mjs --arm baseline --suite transport-verification-v1 --origin https://BASELINE_WORKER_HOST --transport curl
node cloudflare/tools/run-mapping-pilot.mjs --arm candidate --suite transport-verification-v1 --origin https://CANDIDATE_WORKER_HOST --transport curl
```

Original pilot/development runs used an ignored owner-side runner with the same
request serialization and pacing. The checked-in runner is used for follow-up.
No CSV/profile publication, activation, preview confirmation or import is invoked
by these experiments. The optional candidate Worker is removed after deployment
decision; it never receives browser sessions or Java trust secrets.
