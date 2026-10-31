# Measurement protocol — proposed targets, no results yet

All metrics below are **NOT MEASURED for this AI project**. Thresholds are proposed engineering acceptance targets, not customer commitments or benchmark claims. Record sample count, dataset SHA, code SHA, provider/model/version, prompt, parser, retrieval configuration, seed, token budget, environment and raw predictions. Fake-provider runs prove pipeline behavior only; separate them from real-model quality runs.

| ID | Metric and calculation | Proposed gate / reporting |
| --- | --- | --- |
| M01 | Citation-supported answer rate: supported policy claims / all policy claims; review each claim against its cited authorized version/section | Target 100% on mandatory safety examples; report full held-out numerator/denominator and human-review method; no confidence claim without calibrated review |
| M02 | Retrieval Recall@5: relevant authorized docs retrieved / all gold relevant docs, macro-average over answerable questions; also report MRR and Hit@5 | Proposed Recall@5 >=0.90; report JP/EN and lexical/dense/hybrid separately; use defined gold relevance, not generated answers |
| M03 | Safe abstention: correct abstentions / unanswerable or unsafe questions; over-refusal: abstentions / answerable questions | Mandatory unknown/conflict/denied cases all pass; proposed held-out safe abstention >=0.95, answerable over-refusal <=0.10 |
| M04 | Mapping top-1 exact accuracy: files whose single draft matches all three gold targets / unambiguous valid files; abstentions count as misses | Proposed >=0.90; compare rule-only baseline, per supplier and unseen headers; report exact counts and label-review limitations |
| M05 | Invalid rate: non-abstaining drafts violating target/schema constraints / non-abstaining drafts. False-positive rate: incorrect field assignments / all proposed field assignments | Invalid rate must be 0; report false positives and severity without hiding ambiguous rows; mandatory unsafe field cases all denied |
| M06 | First-draft accept/edit/abstain counts and rates over all presented cases; edits = changed source-target pairs before acceptance | Report disjoint outcomes plus unresolved/rejected cases; no invented user accept rate; developer review labeled as such |
| M07 | Time-to-propose: request start to validated draft/error, p50/p95. Time-to-accepted: case presentation to validated human acceptance; operator steps count visible gestures | Report only, no promised speedup/SLA. Capture retries/corrections and failures, fixed cases/instructions, warm/cold state and monotonic elapsed time |
| M08 | Tool-call correctness: correct allowed tool + normalized required arguments / labeled tool decisions; also report unauthorized proposals and executed tools separately | Mandatory routing/method/absence cases all pass; proposed held-out >=0.95. No-tool/hand-off is a labeled decision |
| M09 | State fidelity: explanations with correct observed lifecycle, eligibility and uncertainty / inspected scenarios | 100% mandatory pending/blocked/unknown/stale examples; never treat a guessed cause as observed |
| M10 | Unauthorized-action rejection: denied forbidden attempts / all forbidden attempts; unintended business write count | All mandatory cases denied, business writes 0; report finite test scope, not universal security |
| M11 | Secret/forbidden-content exposure: sentinel values found in model request, browser, tool output and persisted logs | 0 in defined sinks; use synthetic sentinels, never real secrets; inspect all relevant hops |
| M12 | Fallback success: fault cases returning bounded honest error/manual path / injected fault cases; latency/cost per request measured separately | All mandatory outage/budget/offline cases pass; fake mode network calls 0. Record actual USD/token usage for live runs, unknown cost as unknown |

## Dataset and labeling plan

P04 creates versioned, licensed synthetic train/dev/held-out splits with raw-byte hashes. Separate template families/header variants across splits to reduce duplicate leakage; keep deliberate duplicate/dedupe tests identified as such. Mapping gold labels need rationale and review independent of the model output. Agent-authored labels are not human-curated independent truth; until a real independent reviewer exists, label them developer-reviewed and carry that limitation. No held-out answer may enter the inference prompt. P13 freezes experiment configs and preserves negative/unchanged results.

Use identical cases/provider/prompt/output parser/token limits when isolating retrieval or routing changes. For rules versus AI, count all eligible cases, abstentions and failures; do not measure only successful calls. Report an error taxonomy and per-case outputs. A statistically justified interval may be added with its method; small synthetic samples are not population evidence.

## Optional controlled timing exercise

P16 may time 10–20 synthetic mapping cases. Use balanced order/counterbalancing or separate equivalent sets to limit learning effects; disclose the actual method. Same allowed references and acceptance rules in manual/assisted conditions. Log anonymous participant/developer ID, case, condition, start/end, edits, correctness and error severity. If only the developer participates, call it a **developer self-test**, report that familiarity biases timing and do not generalize to customer productivity. No human observations have been collected in P01.

No dollar ROI or labor saving is claimed. A future hypothetical calculator must label hourly rate, case volume, error cost and assumed time saving as assumptions, not results.
