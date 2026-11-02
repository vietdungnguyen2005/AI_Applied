# Independent review packet

The eight labels in `labels.jsonl` are provisional and were written by the agent.
No independent human has signed them off. The run has already occurred; a later
review improves label/response auditability but cannot retroactively make the
author, dataset design or previous analysis blind.

For a first label pass, copy the blank
[`review-template.jsonl`](../runs/new-questions-v1/review-template.jsonl) into a
separate review file. It contains questions, language and collection only; it
does not include the provisional labels or model responses. Inspect the synthetic
[corpus registry](../../../data/v1/corpus.jsonl) and the corresponding source
documents. Use only the specified collection and current, eligible evidence as of
2026-11-02. Record the expected answer or abstention, relevant document/section
references, supporting evidence, reviewer identity/pseudonym and UTC time. For
unknown or conflicting evidence, record what was checked and why it is insufficient
or conflicting. Do not claim completion while reviewer fields are blank.

Freeze the independent label pass before inspecting `labels.jsonl` or the model
outputs. Then compare the labels and review the actual answers for correctness,
complete qualifiers/negation, extraneous material, source relevance and current
access. Record disagreements and rationale in a separate review artifact. The
anchor and citation matches in the automated report are proxies and cannot replace
this semantic review. Never rewrite the original input, label, lock, predictions or
manifest files; corrections require a new explicitly versioned release.
