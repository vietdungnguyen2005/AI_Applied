# P13 final local measurement protocol

Frozen before these calls; no prompt/model/output-parser tuning after results.

Mapping: all 12 original P04 `test` supplier_three inputs, each rule then AI,
same original bytes, declared encoding, selected vendor, fixed standalone fixture
profiles and current E5/PG SOP evidence. These inputs have no recorded P08 model
inference. Labels are pre-existing provisional agent labels, not independent
human gold. Test inference consumes this split even if the model fails. Drafts
are stored only in isolated AI storage; no Java approval or business mutation.
AI mode includes the existing rule guards, so report actual model attempts and
do not call all 12 cases model-selected. Load labels only after all raw outputs
are flushed. Exact mapping and expected-status scores use separate denominators;
missing mapping gold is excluded, not treated as a negative.

QA: all eight already consumed new-questions-v1 questions, exact frozen dense
top-five chunk text reconstructed by chunk ID from retained P06 observations.
Run each question twice through the same local adapter, SYSTEM prompt, supplier,
language, Proposal schema, 512-token limit and strict Proposal/quote validation.
Only the sources array changes: retained candidates versus empty. Both paths
call the model, bypassing AnswerService's early empty/conflict guards equally.
No per-source enum grammar on either path. This isolates evidence availability
at the generator; it is a regression diagnostic, not a new held-out or matched
end-to-end HTTP service benchmark. No source text from labels enters inference.

Pinned Ollama Qwen 3.5 4B Q4_K_M digest from tool-questions-v1 protocol;
4096 context, seed 42, temperature 0.2, thinking false. Mapping uses the unchanged
256-token service limit. No inference retry, cloud fallback, provider calls or
paid charge. Record raw sanitized outputs, token counts, wall times, source Git
SHA, all implementation hashes, input hashes, every failure and summary CSV.
Warmup/startup excluded; sequential n=8/12 timing is not a service SLA. Energy,
hardware cost and actual human corrections are unmeasured. Preserve 11 Java
business table snapshots before/after. Independently reviewed semantic relevance,
mapping gold, real operator task success and business acceptance remain pending.

Run from a clean committed checkout with Docker, existing local E5/Ollama model
and the existing built Project2 artifacts:

```powershell
python -m uv run --frozen --offline python tools/p13_completion.py --project2 D:/CV/Project2 --output .local/p13-final-report.json
python -m uv run --frozen --offline python tools/p13_completion.py --pack .local/p13-final-report.json --output .local/p13-final-package
python -m uv run --frozen --offline python tools/p13_completion.py --verify --output .local/p13-final-package
```

Both outputs must be fresh. The disposable P11 lifecycle owns and removes its
processes/containers. A rerun after inspecting results is explicitly a regression.
