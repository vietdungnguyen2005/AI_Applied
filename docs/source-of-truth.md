# Source of truth and invariants

Status: P02 design. Existing source baseline: Project2 `32d82862526754b46efb774327ccc4774a4decf7`; source evidence is pinned in [P00](evidence/P00-source-index.md). A model, diagram, cached result or suggested mapping is never an authoritative business record.

| Data / decision | Authority | AI permission |
| --- | --- | --- |
| Account/session, enabled role, CSRF, trust headers | Java security + existing BFF | No cookie/CSRF/trust access; only BFF-derived scoped context |
| Vendor existence/active status, catalog, JPY price | Existing Java business API/database | Bounded read facts, no inferred approval or direct DB connection |
| Stock/product version, quantity, reservations | Java transaction and ordered locks | Explanation only; never invent freshness/version |
| Integration profile/version/mapping/activation | Java immutable definition and audit | Draft only; human saves/activates through current protected process |
| Original CSV identity and preview receipt | Original bytes + Java checksum/HMAC | Preserve bytes/hash; cannot mint/use receipt as a tool or normalize authoritative upload |
| Import/work lifecycle, restart eligibility | Java importer/inspection/fenced recovery | Read observed status; no autonomous confirm/restart |
| Reconciliation report | Java persisted report | Read existing GET; never invoke POST to satisfy a read |
| SOP version, provenance and document access | AI-owned curated synthetic collection policy | Authorized ingestion/retrieval; no policy inferred from arbitrary text |
| Embeddings/chunks/index version | AI-owned schema and embedding manifest | Rebuildable derived records, not business truth |
| Mapping suggestion / generated explanation | AI-owned draft with provenance/uncertainty | Untrusted recommendation; may be rejected |
| Eval gold/predictions/metrics | Versioned dataset, label-review provenance and executed runner | Distinguish developer/fake/real evidence; never invent measurements |
| Public deployment revision | Verified deployment attestation | P00 historical live proof is not current parity |

## Non-negotiable invariants

I01: Python has no direct V-Market business database or business write capability.

I02: Every business read is a fixed GET executed by BFF under a currently authenticated OPERATOR request and independently checked by Java. Signed AI context cannot substitute for the user's active Java session.

I03: No unauthorized document content enters retrieval, reranker, model context, citation response, cache or trace. Vendor filters are not tenant authorization.

I04: AI never publishes/activates a business profile, confirms/previews an import as a tool, restarts a job or creates a reconciliation. Human approval remains the existing current workflow, not chat consent.

I05: Original authoritative bytes/encoding/profile/version and existing 5,000,000-byte/1,000-record CSV/65,536-byte JSON limits remain. Mapping target set is exactly sku/name/on_hand; Java JSON direction is target->source.

I06: No stale state is treated as approval. Receipt validity, active profile, global raw-byte dedupe and stock/product guards remain Java's responsibility. A cached AI draft cannot relax them.

I07: `202 != completed`. A timeout/lost response/502/503/504 after a human business mutation is an unknown outcome: inspect, do not blindly retry or declare rollback.

I08: No externally approved spend is inferred from a key or account balance. Fake default; finite opt-in live budget, bounded usage and no paid fallback.

I09: Retrieved documents, CSV cells and tool outputs are data, never agent/system instructions. Code-level allowlists and auth hold independently of model behavior.

I10: Local/mock/synthetic evidence is labeled. Passing schema checks is not runtime security proof, real model quality or customer acceptance.
