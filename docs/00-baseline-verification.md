# P00 — Baseline verification

Date: 2026-10-31 Asia/Bangkok. Environment: Windows 11 build 26200, PowerShell, Java 21, Node v24.12.0, npm 11.6.2, Python 3.12.1, Docker CLI/server 29.3.1, Git 2.51.0.windows.1. Machine-readable baseline: [environment](evidence/P00-environment.json).

AI baseline `62bcc472c2e391235984997b52265460a09da278`; Project2 baseline `32d82862526754b46efb774327ccc4774a4decf7`. Both started clean. Project2 was cloned to the sibling directory; no nested Git repository and no existing checkout overwritten. `audit/p00-baseline` protects AI main from audit changes.

Commands were run from `D:/CV/Project2` unless specified. PowerShell invokes `npm.cmd` and the Windows Maven wrapper. Each command's own exit code is appended to its log, independently of the surrounding shell command status.

| Command | Exit | Observed result | Log |
| --- | ---: | --- | --- |
| `git clone https://github.com/vietdungnguyen2005/Project2.git D:/CV/Project2` | 0 | Clean clone, main at pinned SHA | Baseline metadata |
| `npm.cmd ci` | 0 | 478 packages installed; 479 audited | [install](evidence/logs/P00-npm-ci.log) |
| `npm.cmd run verify` | 0 | 11 test files / 58 tests passed; ESLint, TypeScript, Next build passed | [verification](evidence/logs/P00-npm-verify.log) |
| `backend/mvnw.cmd verify` (cwd backend) | 0 | 115 tests, 0 failures/errors/skips; package and Spotless passed | [Maven](evidence/logs/P00-maven-verify.log) |
| `docker compose config --quiet` | 0 | Compose configuration valid | [Compose](evidence/logs/P00-compose-config.log) |
| `docker info --format '{{.ServerVersion}}'` | 0 | Docker server 29.3.1 reachable | [Docker](evidence/logs/P00-docker-info.log) |
| `npm.cmd run build:worker` | 0 | OpenNext generated `.open-next/worker.js`; no deployment | [Worker](evidence/logs/P00-worker-build.log) |
| `npm.cmd audit --audit-level=high` | 1 | 19 vulnerabilities: 17 moderate, 2 high | [dependency audit](evidence/logs/P00-npm-audit.log) |

Maven ran the existing PostgreSQL/Redis Testcontainers tests against disposable local containers; no `docker compose up` against the named V-Market database was run. The existing test suite already covers operator/CSRF/role revocation, immutable profiles, original-byte preview receipt, CP932, duplicate import, recovery/fencing, checkout, stock and reconciliation. Test names and locations: [source index](evidence/P00-source-index.md). This is baseline coverage, not evidence of a new AI gateway. No coverage percentage or performance improvement was measured.

## Baseline failure and remediation proposal

Dependency audit is a genuine failing baseline gate. In particular, high advisories affect undici through miniflare/wrangler. The audit suggests Wrangler 4.156.0 outside the currently pinned range, and other transitive packages also appear in the report. Do NOT run `npm audit fix --force` as part of P00. Proposed separate change: inspect dependency reachability, update compatible direct/toolchain pins and lockfile, then rerun unit/lint/types/Next/Worker builds plus dependency audit. No claim of exploitation or production impact is made from audit counts alone.

## Unexecuted and limited checks

- Real operator browser QA script and UI scenarios: NOT RUN in P00. Maven and frontend contract tests ran, but they do not substitute for browser proof.
- Backend Docker image build, Helm and Terraform lanes: NOT RUN; phase focuses on listed baseline commands and source audit.
- Public deployment SHA, live smoke, real provider quality, AI CI and cloud deployment: NOT VERIFIED / NOT RUN. Historical live proof is dated 2026-08-20 and pins 5ad16e9; no current public SHA is inferred.
- No AI application test exists yet; existing API probe is preserved and was not rerun, avoiding external quota/spend in this audit.

## Reproduction

On matching Windows tools, clone the pinned Project2 revision, run `npm.cmd ci`, `npm.cmd run verify`, `npm.cmd run build:worker`, then from backend `./mvnw.cmd verify`. Docker must be running for Testcontainers. Run `docker compose config --quiet` from Project2 root. `npm.cmd audit --audit-level=high` is registry-time dependent; compare advisories and actual exit code rather than assuming an immutable count.

Before publishing the evidence, inspect redacted logs and manifest, run `git diff --check`, verify `.env` is ignored and check Project2 remains clean. Logs retain executed output with credential/receipt/header redactions where present; they are not edited to conceal failed tests or audit findings.
