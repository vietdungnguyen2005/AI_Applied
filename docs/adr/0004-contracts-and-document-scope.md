# ADR 0004 — Strict contracts, scoped synthetic documents and CLI evaluation

Date: 2026-10-31. Status: accepted design; implementation pending.

Use OpenAPI 3.1.1 and JSON Schema 2020-12, explicit discriminated unions, closed objects and stable error codes. Python/BFF must enforce runtime byte limits, signature validity, sequence/expiry, argument-to-scope checks, state transitions and citation support beyond schema syntax. Checked examples are contract evidence only.

Document collections are AI access scopes, not vendor tenants. BFF server policy assigns readable collection IDs per current operator; requested vendor/collection filters may only narrow those rights. Local demo scope can grant all synthetic collections to all OPERATORs, explicitly labeled as shared-store demo access. Document authorship is separately configured; default integrated ingestion is OFF. No invented ADMIN role or automatic supplier permission is introduced. Default corpus comes from local curated fixtures. A signed context authorizes only one named operation for its bound request.

Store raw document bytes in the AI volume under generated IDs, reject unsupported/scanned extraction and cap ZIP expansion. Source page/section identifiers survive extraction. Immutable source versions and embedding model/dimension versions keep citations/index rebuilds reproducible. Object storage/remote fetch are deferred. Citation URLs are synthesized by BFF from verified IDs; the model cannot supply arbitrary links.

Evaluation remains an offline CLI over repository-controlled configuration. `/ai/evals` is not exposed; avoiding arbitrary operator-submitted jobs/paths/URLs reduces attack surface. Ingestion and draft persistence are AI-owned mutations, never business changes. No production readiness or universal prompt-injection protection is inferred.
