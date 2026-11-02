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
