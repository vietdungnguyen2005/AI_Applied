# Decisions and open questions

Recorded 2026-10-31. These are engineering decisions for a synthetic portfolio case, not stakeholder approvals. Requirement statuses remain planned.

| ID | Decision / rationale | Evidence or limitation | Revisit |
| --- | --- | --- | --- |
| DEC01 | Prioritize J1–J5 over broad chatbot scope | Source-verified onboarding is a concrete integration surface | If measured user need changes |
| DEC02 | Human approval stays in current protected workflow | F03–F07; receipts and staged jobs already exist | Never bypass to accommodate AI |
| DEC03 | Use fake-default standalone and opt-in integrated local modes | No keys or external spend needed for important CI tests | P03/P09 implementation proof |
| DEC04 | Business tool executor is BFF, Python proposes typed intents | Java session/account revalidation is authoritative | P02 design; P09 auth tests |
| DEC05 | Java mapping JSON remains target -> source | IntegrationProfileService requires exact target key set | P08 adapter tests |
| DEC06 | Only read stored reconciliation reports via existing GET | POST creates reconciliation_run; no by-ID GET exists | Reviewed additive contract only if needed |
| DEC07 | Compare header rules before claiming AI value | No model quality/benefit measured yet | P08/P13 ablation |
| DEC08 | Quality thresholds are proposed and versioned before evaluation | No real discovery/UAT; no ROI evidence | Owner review before frozen held-out run |
| DEC09 | Keep current labels honest | Simulated discovery != real interview; agent labels != independent human review | Genuine reviewer/participant evidence |
| DEC10 | Preserve feature OFF and manual fallback | Public deployment parity unknown; P00 dependency audit failed | P14 security and P15 operations gates |

| Open ID | Question / default | Owner and resolution gate |
| --- | --- | --- |
| O01 | Who independently reviews SOP/gold labels? Default: synthetic developer-reviewed only | Repository owner; P04/P13 limitation until real review |
| O02 | How are policy effective dates/conflicts resolved? Default: no invented precedence, abstain on unresolved conflict | Data owner role to be assigned; P02/P04 |
| O03 | Japanese answer generation scope? Default: bilingual retrieval/fixtures; only claim answer quality actually tested | Repository owner; P07 eval |
| O04 | Actual latency/cost budget? Default: no live calls in documentation phases, fake mode; finite budget required before live use | Repository owner + agent; P03/P15 |
| O05 | Business freshness signal? Default: cannot infer from three columns; explicit warning and human responsibility | Hypothetical operator/data owner; future scope |
| O06 | Baseline advisories and deployed revision? Default: keep R08 open, no public-parity claim | Repository owner + agent; P14/release |
| O07 | Genuine UAT/timing participants? Default: developer self-test only, no customer claim | Repository owner; P16 |

Open questions do not require fabricating answers or blocking documentation/design work. Carry defaults as assumptions, and stop only a dependent claim or action that genuinely needs resolution.
