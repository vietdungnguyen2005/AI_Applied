# P02 source review record

Access date: 2026-10-31 Asia/Bangkok. External research used the Agent Reach skill's native web route. This is a bounded source/standards review for P02, not a broad market research task. No live model API, private data or production business endpoint was called.

| Source | What was actually read | Use / limitation |
| --- | --- | --- |
| [Project2 pinned source](https://github.com/vietdungnguyen2005/Project2/tree/32d82862526754b46efb774327ccc4774a4decf7) | Local backend-proxy, OperatorSessionController, SecurityConfiguration, SessionAccountRefreshFilter, IntegrationProfileService, SupplierOnboardingService, MigrationModels, LegacyImportService, ReconciliationController/Models/Service and V5 import-mode migration | Existing authority/headers/CSRF/receipt/GETs/response projections; no change to the checkout |
| [Official OWASP 2026 publication](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) | Publication page and download target | Confirms edition; PDF link resolved but subsequent content search timed out, so no full 122-page guide review is claimed |
| [Canonical 2026 final list](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/README.md) | Published edition status and complete final risk-ID table | Risk IDs for our original project threat/control mapping; no 2025 ID substitution |
| [OWASP archive landing page](https://genai.owasp.org/llm-top-10/) | Landing page currently showing 2025 labels | Not used as the 2026 numbering source |
| [Official agentic release](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) | ASI01–ASI10 descriptions in release article | Separate agentic control review; attempted alternate /resource/top-10-for-agentic-applications/ URL unavailable, replaced by this accessible primary source |
| [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html) | Official specification, schema/reference/security structure | Pinned contract version; not a claim that this is the newest OAS release |
| [JSON Schema 2020-12 validation](https://json-schema.org/draft/2020-12/json-schema-validation) | Official validation vocabulary, format/content boundaries | Strict schema vocabulary and explicit semantic/runtime limits |
| [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) | Ed25519 algorithm/signature specification and test-vector availability | Signature primitive selection only; no handwritten crypto or interoperability test in this phase |

Descriptions of this project's controls are engineering decisions from source/requirements, not a reproduction of an OWASP guide or certification. Runtime proof must be produced by the implementation phases.
