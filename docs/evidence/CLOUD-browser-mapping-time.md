# Live operator browser mapping benchmark — 2026-11-04

The owner explicitly authorized creating an operator if none had been created.
Render had no bootstrap account configured and the real `auth_account` table was
empty. One dedicated OPERATOR was created with a random BCrypt-12 password;
credentials remain in an ignored local file. No existing password was reset.
The actual browser then signed in at
https://v-market.vmarket-vietdung2005.workers.dev/ops .

This establishes a real signed-in mapping → review → inactive profile creation →
activation → Java preview workflow on the deployed Cloudflare BFF, Render Java
and business PostgreSQL, using the deployed AI Worker
`adc14e47-d3ae-47fd-b830-7ca198a93221`. Browser calls were not intercepted and
neither Java authorization nor model responses were mocked. It does not verify
production import confirmation, stock application, QA or investigations.

## Measurement and result

One informed agent operated the real UI through CUA on three synthetic UTF-8
files. Each file had one verified RIVERBYTE SKU (`VM-002`). Timing starts before
entering CSV and ends after the preview shows the expected mapping, one accepted
row and zero rejected rows. It includes saving and activating an immutable
profile, AI waiting, tool orchestration, inspection and any recovery. Setup,
login and fixture preparation precede the timer. No human typing/thinking delay
was simulated. The agent knew expected mappings; files had already been used in
the mapping diagnostic. This is not an independent file sample or human UAT.

Final full collection, frozen before collection in
[`agent-browser-v3`](../../evals/onboarding-time/agent-browser-v3/protocol.json):

| File change | Manual elapsed | Assisted elapsed | Notes |
| --- | ---: | ---: | --- |
| Product key header | 7.038 s | 9.020 s | Both completed without instrument errors |
| Stock header | 48.081 s | 56.447 s | Manual checkbox driver failure; assisted draft did not render, followed by manual fallback. Recovery times retained |
| Three Japanese headers | 5.600 s | 9.478 s | Both completed without instrument errors |
| Descriptive median, all three | 7.038 s | 9.478 s | Not a causal estimate of human productivity |

All six tasks eventually reached the required real Java preview. The two clean
paired cases were slower with AI; the other pair is contaminated by instrument
recovery. There is **no basis for a CV claim that onboarding time fell by X%**.
The observed medians also do not justify a general claim about how much slower
AI is: the sample is tiny and automation does not reproduce human work.

Manual entry of source-column names was five operations in the manual arm versus
one in the assisted arm (manual fallback). Two of three assisted tasks visibly
received correct drafts; the third displayed no draft before recovery. This is a
UI outcome, not evidence that the model returned an incorrect answer or that the
provider failed. D1 reservations rose from 56 to 58, consistent with only two
additional inference reservations in this collection. The exact reason for the
missing rendered draft was not established. No automatic AI request retry was
made. Saving profiles, activation and review remained necessary in both arms.

Thus the supported narrow effort result is **5 → 1 manual source-column entries
across these three agent-operated tasks**, not measured human labor saved.

## Retained failures and collection history

- `agent-browser-v1`: first trial retained with a harness binding error and a
  real `VENDOR_MISMATCH` rejection for `VM-005`, which belongs to another vendor.
  Its planned two-accepted-row endpoint was never reached. It is invalid fixture
  history, not included in the corrected one-row sample.
- `agent-browser-v2`: all six corrected tasks completed. Raw median manual / AI
  times were 6.740 / 6.609 seconds, but a locator failure in the assisted key task
  and a checkbox failure in the manual Japanese task contaminated the timings.
  Three correct drafts were visibly received and no assisted column entry was
  needed. These results remain intact and are not promoted as a time-saving win.
- `agent-browser-v3`: the entire same paired sequence was frozen and repeated
  once with a corrected combobox locator and state observation before actions.
  The remaining failures and all recovery are retained above. Collection stopped;
  it was not repeated until a favorable number appeared. No runtime/model change
  or new input labels were introduced between V2 and V3.

The original order is manual → AI for the key file, AI → manual for the stock
file, manual → AI for the Japanese file. Both arms begin with `supplier-b` v1,
and use the same shared creation/activation/preview steps. The UI starts with
the current profile mapping, so only changed source fields need manual entry.
For one changed header, AI adds selection, request and waiting overhead while
direct entry needs one field change. These observations motivate measuring the
decision/review work with actual operators before claiming time saved.

## Cleanup, reproduction and boundaries

[Cleanup evidence](../../evals/onboarding-time/agent-browser-v3/cleanup.json): all
13 uniquely named benchmark profiles (one V1, six V2, six V3) were deactivated
through the authenticated normal Java API. Their immutable records/audit history
remain; original `supplier-a` and `supplier-b` stay active. The dedicated account
is retained for the owner's demo. No import confirmation or queue action was
invoked; no inventory change was requested. No backend deployment, migration,
paid model fallback, subscription change or quota reset was needed. Final daily
reservations were 58/60 for UTC 2026-11-03 (local date 2026-11-04).

Inputs, precommitted protocols, CUA workflow source, event timestamps, raw rendered
preview text, errors, screenshots and recomputed reports are under
[`evals/onboarding-time`](../../evals/onboarding-time). In-process timestamps use
`Date.now()`; reports retain failed steps instead of estimating their duration.
The read-only report verifier requires only Python's standard library:

```powershell
python tools/browser_mapping_timing.py --check
```

Live replay requires a real owner-authorized operator session, unused immutable
profile IDs and available inference quota. It writes profiles and should not be
rerun merely to obtain a better number. Offline verification does not log in,
mutate business data or invoke a model. Credentials, cookies, CSRF tokens and
service/database keys are excluded from public artifacts.
