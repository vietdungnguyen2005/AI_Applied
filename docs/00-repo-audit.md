# P00 — Repository audit

Date: 2026-10-31, Asia/Bangkok. All execution in this phase was local. No production endpoint was called or changed.

## Baselines and scope

| Repository | Location | Baseline SHA | Before | After |
| --- | --- | --- | --- | --- |
| AI_Applied | `D:/CV/AI_Applied` | `62bcc472c2e391235984997b52265460a09da278` | Clean, main | Audit documents/logs on `audit/p00-baseline` |
| Project2 | `D:/CV/Project2` | `32d82862526754b46efb774327ccc4774a4decf7` | Fresh clone, clean main | Clean; generated ignored build/dependency artifacts |

AI_Applied is NOT empty: README, `.gitignore`, `.env.example`, API connectivity script and JSON report already exist. They are preserved. The private `.env` remains ignored. There is no FastAPI application, embedding index, AI database or evaluation harness yet. No applicable repository AGENTS.md was found in either checkout or their parent workspace paths.

Project2 uses Java 21, Spring Boot 3.5.16, Spring Security/JDBC Session, Spring Batch, Flyway, PostgreSQL and Redis; Next.js 16.4.2 / React 19.2.8 provides browser UI and BFF. Exact source paths, line numbers, pinned GitHub links, controller mappings, model records, migrations and test names are in [source index](evidence/P00-source-index.md). Architecture and behavior below are source-verified; runtime claims are limited to [baseline verification](00-baseline-verification.md).

## Identity and trust trace

1. Browser `lib/operator-session.ts:9` reads `/api/auth/session`; `operatorFetch` reads the current CSRF token before a mutation. `app/api/auth/[action]/route.ts` only forwards session GET and login/logout POST.
2. `lib/backend-proxy.ts:7` forwards a bounded allowlist including cookie, CSRF and receipt. `buildBackendHeaders` adds server-owned trust credentials, never accepts caller-owned trust headers. Mutation origin checks reject cross-origin requests. It buffers original bytes without decoding, enforces body budgets and separate upload/upstream deadlines. It does not retry mutations.
3. Java `BffAuthenticationFilter` checks the BFF secret before CSRF. `SecurityConfiguration` protects `/api/ops/**` with `hasRole("OPERATOR")`, requires CSRF for unsafe ops/auth methods, disables HTTP Basic and configures JDBC sessions. Cookie is HttpOnly, SameSite Lax, secure by default.
4. `SessionAccountRefreshFilter` reloads the account on every authenticated request, refreshes authorities and invalidates a disabled/deleted user's session. `OpsAuthorizer` independently checks the operations secret at controllers. Trust credentials alone do not authenticate an operator.
5. `OperatorSessionController` returns authenticated status, username, roles AND a CSRF token. A future BFF AI handler must select only the minimum identity result; it MUST NOT forward this entire payload to Python. A successful session GET alone is insufficient: require current `ROLE_OPERATOR`, and let Java reauthorize each business read with the same request's session.

## Existing endpoint and mutation inventory

Paths below are same-origin BFF unless explicitly marked Java-only. They require the current OPERATOR session; mutations additionally require CSRF. BFF injects trust headers server-side. Exact request/response records are captured in the source index and remain authoritative.

| Method / path | Input | Success / response | AI boundary |
| --- | --- | --- | --- |
| GET `/api/ops/integration-profiles` | Session | 200, up to 100 immutable Profile versions including requiredFields/validation | Read-only candidate |
| POST same | Definition JSON: profileId, version, encoding, vendorCode, mapping, skuNormalization | 201 Profile, inactive; duplicate identity 409 | Human only |
| PATCH `/api/ops/integration-profiles/{profileId}/{version}` | `{active:boolean}` | 200 Profile; audited activation/deactivation | Human only |
| POST `/api/ops/onboarding/{profileId}/{version}/preview` | Original text/csv bytes | 200 Preview: profileId, version, encoding, mapping, acceptedRows, rejectedRows, sample, errors, confirmationReceipt | Human workflow, no AI tool |
| POST same `/confirm` | Same bytes, X-Source-Name, X-Preview-Receipt | 202 MigrationSummary + Preference-Applied respond-async | Human only; staged != completed |
| GET `/api/ops/imports` | Session | 200, latest 20 MigrationSummary records | Read-only candidate |
| POST same | CSV, X-Source-Name, X-Source-Encoding, optional Prefer | 202 async or 201 synchronous | Human only |
| GET `/api/ops/imports/{jobId}/inspection` | UUID | 200 Inspection(job, workState, recoveryCount, lastRecoveryReason, restartAllowed, errors) | Read-only candidate |
| GET `/api/ops/imports/{jobId}` | UUID | 200 MigrationSummary | Java-only: no matching BFF route at baseline; do not invent one |
| POST `/api/ops/imports/{jobId}/restart` | UUID, optional Prefer respond-async | 202 queued or 200 terminal replay; active/busy conflict 409 | Human only |
| GET `/api/ops/reconciliations` | Session | 200 latest 20 reports with stored discrepancies | Existing safe READ candidate |
| POST same | `{migrationJobId: UUID}` | 201 persisted ReconciliationReport | Human only; creates records |
| GET `/api/ops/inventory/snapshot` | Session | 200 versioned CSV | Existing manual export, not an AI write |
| GET `/api/ops/orders` | Session | Operations queue | Out of initial AI allowlist |
| POST `/api/ops/orders/{orderNumber}/fulfillment` | Existing fulfillment transition | Audited business mutation | Human only |

General failure contracts: invalid structure 400; missing/invalid authentication or trust 401/403; CSRF denial 401/403 depending authentication; stale/inactive/identity conflict 409; request too large 413. Missing import/profile is currently translated through InvalidImportException (400), so a client must not assume every absent resource returns 404. BFF can return 408 on upload deadline, 502 on invalid/oversize upstream response, 503 unavailable and 504 timeout. These transport failures do not establish transaction rollback. No reconciliation-by-ID GET exists; use the existing recent reports, without fabricating a narrow GET or running the POST as an agent read.

Other business writes are checkout creation, closing unused checkout keys and fulfillment; all remain outside AI tools. Catalog and public tracking reads do not confer operator rights.

## Profile, byte and lifecycle invariants

IntegrationProfileService.Profile.requiredFields is exactly `sku`, `name`, `on_hand`. Mapping JSON direction is **target field -> source header**. Suggestion UI may display source -> target, but a boundary adapter must reverse and validate explicitly. SKU 1–64 chars; name 1–160; on_hand integer 0–1,000,000. Publishing requires exactly three distinct trimmed nonblank source headers <=80 characters, no control characters, existing active vendor, positive version and valid profile ID. Allowed encodings UTF-8/CP932; normalization TRIM/TRIM_UPPER. V14 enforces immutable definitions with a PostgreSQL trigger; changing a definition requires a new version.

SupplierOnboardingService.preview is read-only repeatable-read. Receipt uses HMAC-SHA256 and binds profile/version, actor hash, original-byte checksum, enriched canonical checksum and 600-second expiry. Confirm revalidates receipt and active profile, preserves original checksum identity and stages through LegacyImportService. Duplicate original bytes across other profile versions/legacy routes conflict. Byte changes, including encoding/newlines, create a different identity. Do not normalize authoritative input bytes or infer freshness from file content.

BFF and Java cap CSV at 5,000,000 bytes, JSON at 65,536 bytes; parser caps data rows at 1,000. Headers/width/encoding/duplicate-SKU validation precede or quarantine application as appropriate. Staged rows retain product/stock versions; ImportChunkService locks and applies atomically in groups. ImportRepositoryFence and ImportRecoveryService govern claim generations, leases, metadata fencing and bounded recovery. Unknown outcome requires inspection; no automatic confirm/restart/reconciliation retry.

Migrations V1–V14 exist. V4 owns operator sessions; V5–V9 stock/reconciliation/durable recovery; V10–V13 guest checkout/replay; V14 supplier profile provenance. AI must introduce its own schema/migrations, never modify these for convenience. Compose declares host ports PostgreSQL 5433, Redis 6380, backend 8080; frontend runs separately via npm. AI storage must use distinct ports/volumes and credentials.

## CI and verification

`.github/workflows/ci.yml` has frontend, backend and infrastructure jobs: npm verification/audit/browser QA/Worker build; Maven verify/backend image; Compose/Helm/Terraform validation. The phase ran npm verification, Worker build, Maven verify, Compose config and npm audit. Runtime browser QA, Docker image build, Helm and Terraform were not run in this audit; no claim that all CI jobs passed. Test execution is not a production deployment.

## Deployment revision discrepancy

`docs/evidence/live-deployment.md` records validation on **2026-08-20**, backend revision **5ad16e9**. The current clone is **32d8286**. README says local remediation/onboarding have not been deployed; that sentence cannot mean the fetched source is unpushed, since it is already available from origin. Treat it as a stale rollout statement, not an observed deployment revision. Public deployment SHA was NOT freshly attested, and public endpoints were not exercised. Live artifact parity is unverified. Never reuse old screenshots/benchmarks as evidence for the new AI service.

## Baseline findings

Frontend 58 tests pass; backend 115 tests pass, including existing security, import, stock, checkout and reconciliation coverage. Worker build and Compose validation pass. Dependency audit fails (19 advisories: 17 moderate, 2 high), including undici through miniflare/wrangler. Advisory presence is verified; reachability/exploitability is not assessed. No auto-upgrade or business-code fix is included in P00.
