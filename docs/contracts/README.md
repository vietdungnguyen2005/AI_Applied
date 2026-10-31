# P02 wire contracts — design only

- [OpenAPI 3.1.1](openapi.yaml): eight proposed internal paths; implemented availability is not implied.
- [JSON Schema 2020-12](bff-tool-gateway.schema.json): one source for 25 wire definitions. Root validates ToolIntentEnvelope; OpenAPI and examples reference specific `$defs`.
- [Gateway protocol](gateway-protocol.md): mandatory auth/scope/time/byte/sequence checks beyond JSON syntax.
- [Example cases](examples/cases.json): synthetic positive/negative schema instances, not real provider or session traffic.
- [Validation command](../../tools/validate_contracts.py): local contract QA utility, not product/server code.

Python keys and field names are intentionally sanitized projections, not raw Java response schemas. Closed objects reject arbitrary URLs, SQL, extra roles/secrets and unsupported tool names. A structurally valid scoped context still requires cryptographic verification, current BFF user authorization, replay prevention and actual scope enforcement.

Use maintained implementations of the [OpenAPI specification](https://spec.openapis.org/oas/v3.1.1.html), [JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation) and [Ed25519](https://www.rfc-editor.org/rfc/rfc8032). We pin OpenAPI 3.1.1 for this contract's tooling; this is not a claim it is the newest specification release.

Application semantic checks include distinct trimmed source headers in a mapping, hash of original bytes, profile constraints/ownership, result-to-pending-call correlation, observed data freshness, citation support and scope subsets. Mirror Java's UTF-16 code-unit lengths and ISO control-character checks when adapting profile headers; JSON Schema maxLength counts Unicode code points and alone does not prove Java acceptance. Header/raw-body caps are runtime requirements, not guarantees from `format: binary`, `maxLength` or an OpenAPI extension. FormatChecker is enabled in contract QA; date/UUID format acceptance alone does not establish expiry or identity.

The validator installs/runs only in an isolated temporary virtual environment for P02. No app dependency/lockfile or Project2 source is changed. P03 will establish project-wide tooling. Keep fake/real quality and design/runtime evidence separate.
