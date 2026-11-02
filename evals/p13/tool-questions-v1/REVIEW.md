# Blind review of first-intent labels

Copy the [blank reviewer template](../runs/tool-questions-v1/review-template.jsonl)
to a separate file. It includes each question and allowed synthetic scope, but no
provisional expected tool, argument, model response or score. No reviewer has filled
or signed it. For the first pass, do not open `labels.jsonl`, the recorded model
responses or the analysis until the independent labels are frozen.

For each question, record the appropriate **first** action: a read-only tool intent
or a human handoff. Use the project's closed tool definitions and the explicitly
supplied job UUID/scope. Record exact expected tool and constrained arguments, your
identity/pseudonym, UTC review time and a rationale. For knowledge search, record
whether the query must preserve particular concepts; the current automated scorer
checks only nonemptiness and scope, not semantic query quality. Do not execute a
tool or business action while labeling.

After freezing the independent labels, compare them with the provisional labels and
then inspect outputs for tool choice, argument meaning, error handling and whether a
static guard bypassed the model. Record disagreements and resolve them in a new
versioned artifact. This review does not make the original agent-authored questions
independent customer data; the author knew the tool registry and earlier smoke work.
