# Preregistered first-intent planner comparison

The [11 inputs](inputs.jsonl), [provisional labels](labels.jsonl),
[protocol](protocol.json) and [lock](lock.json) were frozen before this
experiment's local model calls. Inputs contain only question, test ID and a fixed
synthetic scope; labels are read by the scorer after every first-intent response
has been journaled. The developer knew the tool registry and earlier smoke results;
the questions and labels were agent-authored, and independent review is pending.
This is not an independently blind customer or new-domain holdout.

Both variants call the same `AgentService.step` with step zero, empty observations,
the same question and allowed scope: a deterministic fake router and actual local
Qwen 4B. They produce a **planned first intent only**; no tool, Java session or
business action is executed. The static write-action guard applies before both
variants. When it hands off without invoking Qwen, that outcome is evidence of the
guard, not the model's ability to reject a prompt injection. `model_calls` makes
the distinction explicit.

The scorer checks the exact expected kind and tool; for job tools it checks the
exact question-supplied UUID. For knowledge search it checks nonempty query, exact
allowed collection and `top_k`, not semantic relevance of the generated query.
Model/service failures are retained and lower coverage/task completion; they are
not silently removed. Counting forbidden **public validated intents** does not
examine hidden raw model text, prove authorization, or establish a real tool was
called. The semantic correctness of labels and queries remains unreviewed.

The runner requires an already installed digest-pinned Ollama model and a fresh
directory. It never calls an external inference provider, dispatches tools or
modifies Java. It journals all raw validated outputs before parsing labels, records
model digest/runtime/prompt hash/usage/latency, writes per-case results and summary
CSV, and refuses to overwrite a prior run:

```powershell
python -m uv run --frozen --offline python tools/p13_tool_run.py --output .local/p13-tool-run-fresh
```

A repeat after results are inspected is a regression, not another fresh test.
Electricity and hardware costs are not measured; local provider charge is zero.

## Recorded result

The first run completed on 2026-11-02 using source commit
`b37d1e237b55046d2c066a3f803eb8b9384a57f3`; [config, all 22 raw predictions,
per-case scores, summary and hashes](../runs/tool-questions-v1/manifest.json) are
retained. Both the deterministic router and the local Qwen route matched the
provisional first-kind/tool/argument criteria **11/11** on these small synthetic
questions. Four handoffs in **each** variant were produced by the static guard;
the local model was actually called on only seven cases. Consequently the model's
own refusal of the four write/injection requests was **not measured**. Both paths
returned zero forbidden public intents, a consequence observed after the closed
parser/allowlist; hidden raw model output and actual authorization were not measured.

The local route's seven model-call cases had median/p95 **777/1092 ms**, 2,246
prompt and 217 completion tokens returned. The all-11 median/p95 was **664/1071
ms** and includes four fast, model-free guard cases; it is not directly comparable
to an all-model workload. The deterministic path had no model calls. These are
single sequential local measurements, not latency SLAs or generalization claims.
The [independent review packet](REVIEW.md) is still blank.

`python -m uv run --frozen python tools/p13_tool_verify.py --artifact
evals/p13/runs/tool-questions-v1` verifies the frozen protocol/source/model digest,
all 22 journaled case/method identities, scores, summary and artifact hashes
without running a model or executing a tool.
