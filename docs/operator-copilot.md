# Operator Copilot (P12)

The Project2 `/ops` evidence desk is an additive, default-OFF client component.
It reuses the Operations Ledger design and existing human mapping/profile/preview/
confirm flow. The public storefront does not import it. The incremental
`integration/project2-p12.patch` applies after P11 commit
`acec14c5e3c477c47cbd9b5adb7ecf84b27836b1`; Project2 is committed locally only.

| Runtime | Flags and boundary |
| --- | --- |
| Project2 BFF | `AI_COPILOT_ENABLED=true`, `AI_COPILOT_PANEL_ENABLED=true` display the panel; `AI_QA_ENABLED`, `AI_RUNS_ENABLED`, `AI_MAPPING_DRAFTS_ENABLED` independently enable capabilities |
| Python | `AI_MODE=integrated`, `AI_AGENT_ENABLED=true`, trusted Ed25519 public keys; `AI_QA_ENABLED=true` enables signed ask/source reads; runs and mapping retain their own flags |
| Storage/model | Dedicated AI PostgreSQL, loopback host, pinned E5 bundle for local retrieval; fake/local providers only in integrated mode |

Signing/HMAC/Java secrets remain in BFF server environment, never browser code or
Python. Python receives public verification keys only. All flags default OFF in
example configuration; no deployment, persistent key installation or remote
Project2 push is performed. OpenRouter's uncertain-call block is not reset.

Browser QA input is an actual active Java profile ID/version, a bounded question
and en/ja language. The BFF derives its synthetic supplier scope from the current
Java profile, checks session/OPERATOR/CSRF/same-origin before I/O, then rechecks the
same account and unchanged active profile after I/O. It rejects browser actor,
vendor, collection or profile-authority payloads. Signed `POST /ai/ask` verifies
the exact body digest, operation `ask`, step zero, current nonce and scope subset.
It uses the existing extractive QA pipeline, including explicit no-answer states.

Clicking a citation POSTs only the profile reference and chunk UUID through the
BFF to signed `POST /ai/citations/read`, operation `documents_read`. Python checks
current collection grant, effective source, active snapshot and deletion state on
each click. An absent, inaccessible or withdrawn source returns the same public
404. The result exposes a maximum 2,000-character excerpt and typed provenance,
not raw storage metadata. The BFF strips internal source URLs; the UI renders
escaped text in a labelled native dialog with keyboard focus restoration. The
unsigned standalone GET citation route remains absent in integrated mode.

Investigation questions start a durable reference and explicitly resume it as part
of that request gesture. Tools remain the P09 closed read-only registry, at most
three attempts. P12 live resume responses add transient projected observations
from reads actually executed and checkpointed in that request, after current
authorization. Inspect/cancel/start return no live observations. Stored snapshots
keep historical status/count/time summaries and never replay cached document or
Java bodies. Up to five independent previous turn summaries stay in component
memory, without cross-run model memory. Only the run UUID enters session storage.

After timeout, stop or reload, explicit inspection is required. There is no
automatic retry, polling, background resume or business consent in chat. A browser
stop does not assert cancellation; cancel uses the inspected revision. Human
handoff scrolls to the existing current-profile/preview/confirm flow. The UI labels
an investigation separately from authoritative Java import status, including 202
pending. Expiry, lost authority and account changes discard privileged UI state.

This remains a shared synthetic OPERATOR demo over two fixed supplier collections.
No production tenant isolation or general document administration is claimed.
See [current executed evidence](evidence/P12.md); full local Java/PG/E5 browser
acceptance is pending Docker recovery, with an opt-in reproducible runner prepared.
