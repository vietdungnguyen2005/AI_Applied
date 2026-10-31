# P08 retained mapping development comparisons

All original inputs/gold remain in frozen `data/v1`; independent human review is pending. Runs exclude all 12 test mapping cases before input projection/inference. Train/dev/regression are now known development/regression material. No held-out accuracy claim.

- `runs/local-v1`: source 7ab64ea, initial 4B prompt, 38 cases x rule/AI = 76 predictions; AI 3/26 exact mapping gold.
- `runs/local-v2`: source 2c7141c, clarified column/value prompt, same 4B/config/data, AI 19/26; rules 20/26.
- `runs/local-9b-v1`: source 2c7141c, same clarified prompt/config/data except 9B model, AI 16/26; rules 20/26.

Config records actual model digest/runtime, normalized-LF source hashes and label hash; summary seals prediction bytes. Gold is used by the scorer after service inference, never supplied to the model. Profile candidates are server seed fixtures, not candidate definitions from gold. Predictions retain real final service output, input rejection, abstention and per-case error/latency; raw LLM text is not retained. `citation_current_checks` counts current-source checks linked to assignments, not HTTP opens. Actual HTTP citation smoke is separate evidence.

Run offline verification with `make mapping-eval-check` or `python -m uv run --frozen python evals/mapping/analyze.py`. It verifies original bytes, source revisions, output schema/header membership, gold comparisons and saved aggregate checks without loading a model or making HTTP requests. Invalid-published rate measures structural/header validity only; omissions/wrong semantic mappings are measured separately by exact gold matches.

To repeat inference explicitly, set the host launcher's local mapping/E5/AI PostgreSQL environment, choose an installed `AI_OLLAMA_MODEL`, and run `python -m uv run --frozen --offline --extra local-embeddings python -m vmarket_ai.mapping.evaluate --output .local/p08-repeat`. The directory must be fresh. This writes only AI draft/evidence storage, never Java inventory or profiles. Results depend on runtime/model/cache state. The service default method changed to rule after comparison; this runner explicitly selects both methods, so the comparison is unaffected.
