# Personas and journeys

All personas are fictional. The only established integrated role is the current V-Market OPERATOR; support engineer, supplier contact and administrator are responsibilities, not new implemented roles or permissions.

| Persona | Responsibility | Permission boundary |
| --- | --- | --- |
| Operator | Select supplier, review draft, preview/confirm, inspect results | Existing active OPERATOR account required for integrated ops |
| Support engineer | Explain faults and guide recovery | No implicit access; needs current authorized OPERATOR session for business reads |
| Supplier contact | Clarify file meaning/encoding/freshness | No supplier login, direct API or catalog write introduced |
| Administrator/data owner | Own account lifecycle, SOP review and feature rollout | No new admin UI or privilege escalation; approval role is procedural |

Fixtures named below are **planned P04 fixture IDs**, not files already created. Metric definitions and proposed thresholds are in [success metrics](success-metrics.md). Acceptance IDs are in the [matrix](acceptance-matrix.md).

## J1 — Grounded supplier SOP answer

Desire D01: find the current procedure with a usable citation. Assumption A01: a synthetic bilingual corpus is sufficient to exercise this. Existing behavior: Project2 has no AI knowledge QA.

Flow: authorized operator selects a supplier collection -> asks a policy question -> assistant retrieves permitted current sources -> returns supported answer with document/version/section citations, or abstains on absent/conflicting evidence. Opening a citation requires the same document authorization.

Fixtures: FX-SOP-A-JA, FX-SOP-B-EN, FX-SOP-OLD, FX-SOP-CONFLICT, FX-SOP-INJECT. Evidence: held-out questions, relevant-source labels, actual retrieved IDs and answer/citation outputs; deny tests must prove no forbidden text reaches context. Metric: M01 citation support, M02 retrieval recall and M03 abstention. Risks: unsupported claims, stale version and malicious document instructions. Rollback: disable QA and show the approved document/manual SOP path without fabricated answers. Cases AC01–AC04, AC19, AC20.

## J2 — Draft mapping from original CSV

Desire D02: inspect a suggested header mapping and edit uncertainty. Assumptions A02/A03: a rule baseline may suffice; AI cannot infer freshness. Existing facts F01–F05: Java permits exactly three target fields and owns profile validation/approval.

Flow: choose canonical vendor and declared encoding -> supply original synthetic bytes -> inspect source header/target/provenance/warnings -> correct draft -> human publishes an inactive profile through the protected process, activates it and previews original bytes. AI cannot invent price, stock versions or vendor ownership. The UI view source -> target must adapt to Java target -> source JSON deliberately.

Fixtures: FX-CSV-A-CP932, FX-CSV-B-UTF8, FX-CSV-AMBIGUOUS, FX-CSV-DUPHEAD, FX-CSV-BADWIDTH, FX-CSV-WRONGENC, FX-CSV-DUPSKU, FX-CSV-VENDOR. Evidence: original hashes, gold mappings/rationale, strict schema outcomes, edits and Java rejection assertions. Metric: M04 exact mapping, M05 invalid/false-positive rates, M06 accept/edit/abstain distribution and M07 time to accepted. Risks: plausible wrong mapping, wrong encoding, silent byte mutation. Rollback: discard draft; continue existing profiles/manual review. Cases AC05–AC10, AC16, AC22–AC24, AC28.

## J3 — Explain a failed or pending import

Desire D03: understand observed state and the next safe human step. Assumption A04: authorized bounded GETs can support an explanation. Existing facts F06/F07/F09: session-authenticated inspection and stored reconciliation reads exist; report creation and restart are writes.

Flow: authorized request -> BFF revalidates identity and executes fixed inspection GET -> sanitized result -> explanation distinguishes observed status, hypothesis and unknown cause. Cite job ID and observation time. A FAILED job's restart eligibility must come from Java. A missing job is not silently changed to an invented 404. A reconciliation report outside latest-20 reads is unavailable unless a reviewed contract is added later.

Fixtures: FX-JOB-FAILED, FX-JOB-PENDING, FX-JOB-BLOCKED, FX-JOB-MISSING, FX-REPORT-ABSENT. Evidence: actual tool trace, sanitized payload, expected explanation assertions and denial/timeout cases. Metric: M08 correct read-tool/arguments and M09 state-faithful explanation. Risks: stale snapshot, invented root cause, unsafe restart recommendation. Rollback: display inspection/manual refresh and escalation, with no mutation retry. Cases AC11–AC14, AC21, AC27.

## J4 — Human-owned approval handoff

Desire D04: know exactly where AI assistance ends. Existing facts F03–F06/F07: immutable profile, activation, preview/confirm, CSRF and receipts remain human controlled.

Flow: ask to import/activate/restart -> AI may explain steps and hand off -> authenticated operator reviews exact scope in current workflow -> explicit human confirmation -> 202 remains pending -> inspect terminal result. No text such as “approve” in chat becomes business authorization. Lost/502/503/504 outcome requires inspection before a human retries.

Fixtures: FX-ACTION-WRITE, FX-RECEIPT-EXPIRED, FX-RECEIPT-TAMPER, FX-PROFILE-INACTIVE, FX-STOCK-STALE, FX-ACK-LOST. Evidence: tool denial trace and DB before/after on rejected actions; explicit gesture and pending UI proof in later integration/browser tests. Metric: M10 forbidden-action rejection and M09 state fidelity; all invariant cases must pass. Risks: conversational approval mistaken for receipt, stale state, duplicate application. Rollback: disable AI flag, preserve manual workflow; never undo legitimate business changes automatically. Cases AC15–AC18, AC25, AC26.

## J5 — Safe refusal and manual fallback

Desire D04: fail clearly when evidence, authorization or input is insufficient. Assumptions: no silent permission, encoding or vendor inference; availability should not force bypasses.

Flow: detect unknown policy, wrong vendor, malformed CSV, denied/expired/revoked session or unavailable provider -> refuse/abstain with bounded reason -> expose only authorized remediation -> preserve original file and existing manual route. Do not disclose existence/content of forbidden documents or invent a successful import.

Fixtures: FX-AUTH-GUEST, FX-AUTH-REVOKED, FX-DOC-DENIED, FX-CSV-VENDOR, FX-CSV-WRONGENC, FX-PROVIDER-DOWN, FX-SOP-INJECT. Evidence: negative test payloads, redacted logs, absence of secret/forbidden content and DB changes, fallback browser proof. Metric: M03 abstention, M10 rejection, M11 secret exposure and M12 recovery/fallback. Risks: over-refusal or a false claim of isolation. Rollback: manual ops, with scoped service outage message and correlation ID. Cases AC03, AC04, AC09, AC10, AC19–AC24, AC29, AC30.
