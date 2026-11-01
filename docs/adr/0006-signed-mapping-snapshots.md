# ADR 0006: current profile snapshots and original-byte JSON mapping transport

Status: implemented for opt-in P10 synthetic local integration, 2026-11-01.

The browser selects a source profile ID/version and declares encoding. BFF checks
current OPERATOR/CSRF and reads Java profiles using the existing protected GET.
It derives vendor, normalization/mapping and the one allowed public synthetic SOP
scope. Only this BFF-owned snapshot enters Python; a client cannot supply vendor,
actor or candidate definitions. Session and active profile are re-read before a
draft returns. This is a current profile snapshot, not proof of CSV row validity,
vendor active state at a later write or multi-tenant authorization.

The P02 planned raw text/csv AI transport becomes an exact signed JSON wrapper
`IntegratedMappingRequest`: original base64, declared encoding/vendor/profile IDs,
method/synthetic declaration and one active profile candidate. This extends the
existing P08 standalone JSON form without changing it. The signed request digest
uses application/json and hashes exact wrapper bytes; its seven metadata lines
are empty because authoritative fields are in the signed body. Source/vendor
headers are rejected. Raw bytes remain bounded at5,000,000; wrapper intake is
bounded at6,700,000. No decode/re-encode or normalization of the original file is
allowed. Shared schemas/OpenAPI and request boundary reflect these limits.

Python validates matching profile/vendor/encoding/IDs, scope, step0 and signature,
then uses the existing mapper/store under a request-scoped policy. Results mark
vendor_verification=bff_profile_snapshot. Standalone continues to say
standalone_fixture. BFF validates output and checks original SHA256; the browser
gets untrusted draft data, bounded current SOP evidence and the source profile.
Rule-only stays default because P08 measured it better on known cases. Local AI
is explicit; external/paid inference is unsupported by this operation.

Only the human client calls the unchanged Java protected publication, activation,
preview and confirm endpoints. Publication creates an inactive immutable version.
Each mutation needs its own user gesture and fresh CSRF; no tool is added to the
closed agent registry. Java's text/csv, original-byte receipt, 600-second validity,
active-profile/vendor, idempotency and concurrency contracts remain unchanged.
Python receives no Java session/CSRF/trust/signing private secret and has no
business API client. AI storage contains drafts/nonces only.

Unknown write outcomes lock the local UI for explicit inspection, not automatic
retry. These guards are not durable across browser reloads; Java remains the
authority across tabs/processes. P11 handles durable agent state separately.
