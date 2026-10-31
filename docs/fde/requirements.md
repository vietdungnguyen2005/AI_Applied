# Requirements — proposed P01 scope

No requirement below is implemented or runtime-accepted in this phase. Priority P0 = mandatory correctness/safety gate; P1 = core capability; P2 = optional enhancement. Origin F/D/A refers to the [fact/desire/assumption register](problem-statement.md). All customer desires are hypothetical. Trace acceptance IDs in [matrix](acceptance-matrix.md).

## Functional requirements

| ID | Priority | Requirement | Origin | Journey / phase | Acceptance |
| --- | --- | --- | --- | --- | --- |
| FR01 | P1 | Answer authorized supplier SOP questions with inspectable document/version/section citations | D01,A01 | J1 / P05–P07 | AC01,AC02 |
| FR02 | P0 | Abstain on missing, stale-only or conflicting policy evidence; disclose uncertainty without inventing resolution | D01 | J1,J5 / P07 | AC03,AC04 |
| FR03 | P0 | Filter document access before retrieval/model context and reauthorize citation opening | D04,F10 | J1,J5 / P05,P07 | AC02,AC19 |
| FR04 | P1 | Suggest only sku/name/on_hand from declared-encoding original CSV; include warnings, provenance and unmapped/uncertain fields | F01,F02,D02 | J2 / P08 | AC05,AC06,AC07,AC28 |
| FR05 | P0 | Preserve raw file/hash; validate encoding, header uniqueness, width, byte/record limits; never silently repair authoritative input | F02,F08 | J2,J5 / P04,P08 | AC08,AC09,AC10,AC22,AC23 |
| FR06 | P0 | Do not infer canonical vendor, price, expected versions or freshness as approved facts | F01,F02,A03 | J2,J5 / P08 | AC07,AC24,AC28 |
| FR07 | P1 | Show editable mapping draft and explicit source->target to Java target->source adapter validation | F01,D02 | J2 / P08,P10 | AC05,AC06,AC16 |
| FR08 | P1 | Explain authorized job/work state and allowlisted row errors using observed inspection and timestamp | F06,D03 | J3 / P09 | AC11,AC12,AC13 |
| FR09 | P0 | Execute only closed read-only tools under current BFF operator authorization, no arbitrary method/path/header/SQL | F07,D04,A04 | J3,J4,J5 / P09 | AC11,AC15,AC20,AC21 |
| FR10 | P1 | Read existing reconciliation reports only; report unavailable if absent; never generate one as a read tool | F09,D03 | J3 / P09 | AC14,AC27 |
| FR11 | P0 | Hand off profile create/activate, preview/confirm, import/restart and other business mutations to the existing explicit human workflow | F03–F07,D04 | J4 / P09,P10 | AC15,AC16,AC17,AC18 |
| FR12 | P0 | Display 202 as pending; transport failure as unknown when appropriate; inspect before any human write retry | F06 | J3,J4 / P10,P12 | AC12,AC25,AC26 |
| FR13 | P0 | Deny guest/revoked/expired/non-operator access without leaking business or document content | F07,D04 | J5 / P09,P14 | AC19,AC21 |
| FR14 | P1 | Remain runnable standalone with deterministic fake providers/mock tools, and preserve manual integrated ops fallback | A04 | J1–J5 / P03,P09,P12,P15 | AC29,AC30 |
| FR15 | P1 | Record sanitized correlation, actual tools, observation times and evaluation outputs for reproducibility | D03,D04 | J3,J5 / P03,P09,P13 | AC11,AC13,AC30 |

## Nonfunctional requirements

| ID | Priority | Requirement | Phase / acceptance |
| --- | --- | --- | --- |
| NFR01 | P0 | Python never receives browser cookie, CSRF token, Java trust secret or business DB credential; browser never receives model key | P02,P09,P14 / AC20 |
| NFR02 | P0 | Reauthorize each privileged tool step; no executable privileges after request deadline/cancellation or on stale resume | P09,P11 / AC21,AC30 |
| NFR03 | P0 | Enforce AI read-only business boundary in code independent of prompt/model output | P09,P14 / AC15,AC20 |
| NFR04 | P0 | Preserve Java upload budgets, receipts, global checksum identity, active profile checks and product/stock fencing | P08–P10,P14 / AC17,AC18,AC22,AC23,AC24,AC25 |
| NFR05 | P0 | Use synthetic data only; no arbitrary user URLs or unrestricted web/file/SQL tools | P04,P05,P09 / AC19,AC20 |
| NFR06 | P0 | Fake default; live provider opt-in with explicit finite budget, usage records and no paid fallback by default | P03,P15 / AC29,AC30 |
| NFR07 | P1 | Report actual latency/cost and deterministic quality metrics under fixed config and frozen held-out datasets | P04,P13 / AC01,AC05,AC11,AC29 |
| NFR08 | P1 | Isolate AI database/schema/ports/volumes from Java business storage; no AI direct business DB connection | P02,P03,P15 / AC20,AC29 |
| NFR09 | P1 | Redact sensitive input/account/header data from logs; document retention and avoid cross-session result reuse | P03,P09,P11 / AC19,AC20,AC21 |
| NFR10 | P1 | Basic keyboard/screen-reader/responsive access; flag OFF by default; public storefront unchanged | P12 / AC16,AC26,AC30 |
| NFR11 | P0 | Label simulation/mock/local/live results; keep command logs/config/data SHA and failures; no fabricated ROI or quality claims | All phases / AC29,AC30 |
| NFR12 | P0 | Re-run relevant Project2 regressions for integration changes; remediate/review baseline dependency findings before security/release acceptance | P09,P10,P14 / AC17,AC18,AC25,AC30 |

## Proposed quality gate

All P0 acceptance scenarios must pass in the implemented mode being claimed. A fake-only test does not satisfy an integrated authorization or business-DB assertion. Quality thresholds and sample-size limitations are in [metrics](success-metrics.md). If a gate cannot be executed, mark it BLOCKED or NOT RUN. Do not lower a threshold after inspecting held-out results without a new version and an explicit explanation.
