# Post-delivery fix — reuse current signed profile mappings

Date: 2026-11-02 Asia/Bangkok. Previous delivery: `1208095`. Implementation
`b5caa02`, integration fixture update `62a8dec`; Project2 remains unchanged at
local `39fbf11b03c1cbd8a59a803f9d2df05a2b131511`.

## Defect and resulting behavior

The mapper used frozen standalone aliases even when the BFF had supplied a
current active Java profile mapping those exact input headers. A correctly
reviewed custom profile could therefore produce an empty/abstained draft simply
because its column names were outside the seed aliases. The new signed endpoint
test reproduced an empty assignment set before the fix.

For one current signed profile, matching vendor/encoding/reference, all three
distinct exact headers now produce `SIGNED_PROFILE_BASELINE`. The rule basis and
assignment reason identify deterministic profile reuse. This path also skips the
model for an `ai` request, avoiding unnecessary generation and conflicting generic
aliases. Input bytes/hash, row/quantity/duplicate checks, human acceptance and
post-read BFF profile revalidation remain in force. No import/profile activation
is performed by the Python mapper.

Unsigned standalone candidates and incomplete matches do not gain this authority.
Standalone aliases and the original consumed P13 benchmark are unchanged. This
fix does **not** establish better unseen model accuracy or change AI2/10 to a
new score. It follows the original frozen delivery snapshot; that manifest remains
a historical snapshot rather than being rewritten as fresh independent evidence.

## Executed verification

- Four new cases: signed exact custom-header mapping; AI request bypasses model
  despite generic alias conflicts; unsigned candidate cannot confer authority;
  missing reviewed header does not infer a match.
- Focused mapping/gateway suites: **46 passed, one PG opt-in skip**.
- Full local suite: **376 passed, eight PG opt-in skips**, 44.72 seconds. CI
  separately provisions real PG and executes its eight marked cases.
- Ruff lint/format and mypy66 pass. An intermediate helper line-length warning
  was fixed before final checks/publication.
- [Real disposable Java/BFF/Python report](POST-profile-reuse.json): explicit
  operator fixture publishes inactive profile, activates it, then requests both
  rule/AI drafts. Each returns200 with exact mapping/no differences and required
  human acceptance. Mapping-phase count/hash snapshots of11 business tables are
  unchanged. Explicit fixture deactivation then makes the next draft return409.
  Operator fixture setup is intentionally outside the read-only comparison.
  Configured provider is fake and model calls/external provider calls are zero.

The first integration attempt stopped during fixture activation because the
test-only read proxy did not relay PATCH. The relay gained PATCH support for
explicit operator setup; no production AI tool method/allowlist changed. The
failed original report/log is retained privately and a fresh v2 report passed.
There was no model inference retry, held-out tuning or business import.

Reproduce after preparing the current Project2 build/JAR and Docker:

```powershell
python -m uv run --frozen python tools/profile_mapping_smoke.py --project2 <prepared-Project2> --output <fresh-report.json>
```

This command owns disposable processes/databases and cleans them afterwards;
it needs no model bundle or provider key. The original Project2 checkout and
user PostgreSQL remain untouched. Independent mapping-quality and human UAT
gates in the P16 honesty report remain open.
