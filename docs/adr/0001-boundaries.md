# ADR 0001 — Independent AI service, Java business authority

Date: 2026-10-31. Status: accepted for implementation design; runtime verification pending.

Context: V-Market already has sessions, immutable supplier profiles, byte-bound receipts, durable imports and reconciliation. Recreating these inside AI would create competing truth and new privilege paths.

Decision: Python owns AI artifacts/storage only. BFF is the sole integrated broker; Java remains authoritative for business reads/writes and human approvals. AI business tools are a closed GET allowlist. No shared database schema/credential or queue. New BFF routes are additive, feature OFF by default; public storefront/manual flows stay unchanged.

Rejected alternatives: direct Python-to-Java shared-secret calls (no end-user authorization); AI-owned import endpoint/queue (competing lifecycle); AI business DB access (bypasses guards); making profile/confirm write tools (violates human ownership).

Consequences: integration requires real local session/role/CSRF regression tests. BFF orchestration is additional work, and Java list bounds limit report/history access. Standalone mocks are available when integration is blocked, but are never advertised as real operator-security proof.

Trace: FR09–FR13, NFR01–NFR04; [I01–I07](../source-of-truth.md), [gateway protocol](../contracts/gateway-protocol.md).
