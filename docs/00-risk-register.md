# P00 — Risk register

Owners: implementation agent = code/doc work; repository owner = acceptance, production decisions, genuine human review. No production changes authorized by this plan.

| ID | Severity | Risk | Control and verification | Owner / state |
| --- | --- | --- | --- | --- |
| R01 | Critical | Python receives browser/session/Java trust secrets | BFF selects minimal sanitized payload; sentinel-secret propagation tests | Agent / planned P02,P09 |
| R02 | Critical | Revoked/non-operator session drives tools | Current session + ROLE_OPERATOR preflight, Java per-action checks, no background privileges | Agent / planned P09 |
| R03 | Critical | LLM selects mutations/arbitrary URL/SQL | Typed closed read-only allowlist enforced independently of model | Agent / planned P09,P14 |
| R04 | Critical | CSV normalization bypasses identity/receipt | Preserve raw bytes/hash, strict declared encoding, existing human confirmation only | Agent / planned P04,P08,P10 |
| R05 | High | 202/timeout misrepresented as success/failure | Render pending/unknown; inspect existing job, no automatic write retries | Agent / planned P10–P12 |
| R06 | High | Document/tool prompt injection | Treat retrieved text as data; ACL filter before retrieval; deny tool escalation | Agent / planned P05–P09,P14 |
| R07 | High | Vendor treated as tenant boundary | Shared-store operator model explicitly documented; no fake isolation claim | Agent / open design constraint |
| R08 | High | Baseline dependency advisories | npm audit exit 1; update supported dependency chain in a separate reviewed change and rerun both builds | Owner + agent / OPEN, 2 high +17 moderate |
| R09 | High | Live/local revision mismatch | Pin code SHA, distinguish historical live proof; no deploy claim without attestation | Owner / live parity unverified |
| R10 | High | External API spend / quota exhaustion | Fake default; live opt-in, finite explicit budget, usage tracking, no paid fallback | Agent / planned P03,P15 |
| R11 | High | Unsupported/scanned documents silently indexed | Reject unsupported extraction; quality metadata; negative parser tests | Agent / planned P05 |
| R12 | Medium | Japanese lexical tokenization weak | Separate lexical/dense baselines and per-language metrics | Agent / planned P06 |
| R13 | High | Gold leakage / fabricated benchmark | Frozen held-out hashes and reproducible raw predictions; fake tests labeled plumbing only | Agent + owner / planned P04,P13 |
| R14 | High | Existing import/stock/checkout regression | Preserve contracts; rerun 115 backend and 58 frontend baseline tests plus new integration cases | Agent / baseline passing |
| R15 | Medium | Log/evidence secret leakage | Redact actual keys, receipt/cookie/auth fields; staged-content scan before push | Agent / P00 scan required |
| R16 | Medium | Local services collide / mutate existing DB | Isolated AI DB/ports/volumes; Testcontainers for baseline, no compose up | Agent / P00 respected |
| R17 | Medium | Durable AI state outlives authorization | TTL, bounded steps/deadline, reauthorization on every resumed tool | Agent / planned P11 |

No critical broken business invariant was observed in executed baseline tests. Passing tests do not prove universal security. P00 identifies R08 without fixing it; a later security/release gate remains blocked until reviewed remediation and regression evidence exist.

## P02 design follow-up (2026-10-31)

R01–R07 and R09–R17 now have detailed proposed controls in [architecture](architecture.md), [gateway protocol](contracts/gateway-protocol.md), [data model](data-model.md) and [threat model](threat-model.md). This is a design update, not a closed runtime risk. R08 remains OPEN at the P00 observed advisory count; no dependency remediation or fresh audit is claimed in P02. Signature/replay, between-step revocation, byte/ACL enforcement and schema-to-handler conformance remain unchecked runtime gates in the [review checklist](design-review-checklist.md).
