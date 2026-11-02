# Optional human benchmark and hypothetical ROI

## Current status

**NOT RUN.** There are no real participant observations or developer timed
manual-versus-assisted trials. Automated browser gestures are engineering tests,
not a human productivity benchmark. The 12 mapping test inputs have now been
consumed by model evaluation and are familiar to the agent; reuse cannot become
an independently unseen evaluation. Do not infer a labor saving from token latency.

## Protocol for a future exercise

Recruit genuine consenting participants through the owner, or clearly name the
experiment a developer self-test. This run sends no recruitment messages. Freeze
10–20 new synthetic mapping cases, independently reviewed gold and acceptance
rules before trial. Use the same reference policy, original encodings, hardware
and Java acceptance criteria in manual/assisted conditions. Counterbalance order
or use independently matched case sets to reduce learning effects. Record whether
the participant previously saw each case; do not call familiar cases blind.

Start timing at case presentation, stop only at correct reviewed acceptance or
explicit unresolved rejection. Count corrections, retries, timeouts and failures.
Capture disjoint accepted/edited/abstained/unresolved outcomes and error severity;
do not count a faster wrong mapping as a success. Keep anonymized raw observations
separate from labels and freeze them before aggregation. Report sample size and
all denominators; no population/ROI conclusion from one developer.

Blank observation schema (no row has been filled): participant pseudonym,
condition/order, case ID/hash, familiarity, start/end UTC, monotonic seconds,
initial/final mapping, corrected pairs, accepted correctness, unresolved status,
error severity, tool/model/config versions and reviewer notes. Store consent
outside the public repo; never include personal or real supplier records.

## Assumption-only calculator

`tools/roi_scenario.py` requires explicit `--cases`, `--minutes-saved`,
`--hourly-cost`, `--monthly-cost`, `--implementation-cost` and `--months` inputs.
Every result is labeled hypothetical, with all assumptions echoed. Use the same
currency for every cost. Negative assumed minutes saved produce a loss; zero
total cost yields undefined ROI, not infinity.

Monthly assumed labor value = cases × minutes saved /60 × hourly cost.
Window cost = implementation cost + monthly operating cost × months.
Window net value = assumed labor value × months − window cost.
Assumed ROI fraction = window net value / window cost when nonzero.

No values in this calculator are inferred from this project's observed latency
or mapping accuracy. No actual customer dollar return, labor saving or payback
period has been measured or claimed.
