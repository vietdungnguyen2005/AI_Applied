# Customer demo storyboard — future local synthetic demo

**This is a proposed script, not a recording or executed demonstration.** No AI interface exists at P01. Use only synthetic data. Label fake versus real provider mode and show exact code/data version. Do not reuse Project2's existing screenshots as AI evidence.

## Three-minute story

| Time | Planned action | Spoken explanation | Evidence to capture later |
| --- | --- | --- | --- |
| 0:00–0:20 | Show local mode, fixture label and operator session | “This fictional retailer uses one shared store. Today we are showing a local synthetic workflow.” | Environment, SHA, provider mode |
| 0:20–0:55 | Ask a supported supplier SOP question; open citation | “The answer identifies its source and version. A missing policy produces no answer.” | J1 actual answer/citation and no-answer case |
| 0:55–1:35 | Load original A CP932 or B UTF-8 bytes; review mapping | “These are suggestions for three allowed targets. The original bytes stay unchanged. We can edit or reject this draft.” | Hash, headers, target/provenance, correction |
| 1:35–2:05 | Ask why an import failed | “The assistant reads current authorized inspection data. It distinguishes an observed error from a hypothesis.” | J3 real GET trace and observation time |
| 2:05–2:35 | Ask to activate/import; show handoff | “The assistant cannot perform this business action. The operator uses the existing protected review and confirmation flow.” | Denied write intent; explicit human gesture if integration ready |
| 2:35–3:00 | Show pending/unknown outcome and manual fallback | “Accepted does not mean completed. We inspect the job, and manual operations remain available if AI is down.” | Pending state, fault path, honest limits |

Do not rush through a receipt or hide a 429/error to meet timing. If an integration gate is blocked, show standalone only and state exactly what is mocked.

## Ten-minute extension

Spend two minutes on the fictional problem/current workflow, three on J1/J2, two on authorized inspection and human handoff, two on malicious/ambiguous input and model-outage fallback, and one on measured evaluation/limitations. Show raw eval counts and a failed example only after P13 executes them; until then say “not measured.”

## Operator checkpoints and rollback

Confirm the selected vendor, declared encoding, original file identity, active profile version, current preview, rejected rows and exact change scope before a human action. Use disposable local business data for the integrated demo. No production mutation is part of this storyboard. A timeout after confirmation requires inspection; no automatic replay or replacement file. Turn the AI feature OFF to return to the existing manual operations path; do not reverse legitimate imports as demo cleanup.

Expected review questions: Which steps are real versus mocked? What evidence supports this answer? Could this call change inventory? What happens if my session expires? What did the benchmark actually measure? Answer using captured traces and phase evidence, not architectural intent.
