# ADR 0002 — Signed scoped requests and a bounded BFF tool loop

Date: 2026-10-31. Status: accepted design; signature interoperability, replay and live-session tests pending P03/P09.

Decision: BFF signs a short-lived Ed25519 AI-specific context bound to method/path/selected metadata/raw-body digest. BFF alone owns the private key; Python gets only the public key. Context contains opaque actor/scope/correlation/nonce/budget identifiers, no raw cookie/CSRF/Java secret. It is never included in an LLM prompt. BFF derives scopes from server policy, ignores browser/model assertions, rechecks active OPERATOR before each action and protected final response, and Java independently authorizes each GET.

Use one explicit controller loop: max 4 model calls, max 3 business tools, one outstanding call, 30-second total deadline. BFF stores pending call/correlation in the live request closure; it accepts only the exact next step/result. No Python callback into Java or BFF executor; no polling/background authority after the request ends. A future resume starts a new authorized request, not a replay of old privilege.

Alternatives rejected: forwarding `/auth/session` directly (leaks CSRF); static API key plus caller-supplied role (no user verification); HMAC signing key shared with Python (Python could mint contexts); a transferable Java access token invented for this project (changes auth); framework-managed unbounded agent actions (harder to enforce ownership/lifetime).

Consequences: key provisioning/rotation and body/metadata binding tests are required. Signatures authenticate integrity, not confidentiality; verified TLS or an explicitly limited same-host private network is still necessary. Compromised BFF or AI host is outside model-level protection; least privilege and operator rechecks still reduce the model's authority. BFF account-to-actor pseudonymization key is separate and never sent to Python.

Implementation protocol and all remaining runtime-only constraints: [gateway protocol](../contracts/gateway-protocol.md). Ed25519 is specified in [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032); use maintained library implementations, not handwritten cryptography. The choice here is project design, not an RFC endorsement of the entire gateway.
