.PHONY: install lint typecheck test contracts dataset-check ingestion-demo retrieval-eval-check mapping-eval-check p13-regression p13-check migrate run
install:
	python -m uv sync --locked
lint:
	python -m uv run --frozen ruff check src tests migrations tools/validate_contracts.py tools/p09_local_smoke.py tools/p10_local_smoke.py tools/p10_checks.py tools/p11_local_smoke.py tools/p11_checks.py tools/p11_proxy.py tools/p12_checks.py tools/p12_local_smoke.py tools/p12_model_smoke.py evals/retrieval/analyze.py evals/mapping/analyze.py evals/p13/verify.py tools/p13_new_questions.py tools/p13_new_pack.py tools/p13_new_verify.py tools/p13_tool_run.py tools/p13_tool_pack.py tools/p13_tool_verify.py
	python -m uv run --frozen ruff format --check src tests migrations tools/validate_contracts.py tools/p09_local_smoke.py tools/p10_local_smoke.py tools/p10_checks.py tools/p11_local_smoke.py tools/p11_checks.py tools/p11_proxy.py tools/p12_checks.py tools/p12_local_smoke.py tools/p12_model_smoke.py evals/retrieval/analyze.py evals/mapping/analyze.py evals/p13/verify.py tools/p13_new_questions.py tools/p13_new_pack.py tools/p13_new_verify.py tools/p13_tool_run.py tools/p13_tool_pack.py tools/p13_tool_verify.py
typecheck:
	python -m uv run --frozen mypy
test:
	python -m uv run --frozen pytest -q
contracts:
	python -m uv run --frozen python tools/validate_contracts.py
dataset-check:
	python -m uv run --frozen python -m vmarket_ai.datasets.generate --check
ingestion-demo:
	python -m uv run --frozen python -m vmarket_ai.ingestion.demo --report .local/ingestion-demo.json
retrieval-eval-check:
	python -m uv run --frozen python evals/retrieval/analyze.py
mapping-eval-check:
	python -m uv run --frozen python evals/mapping/analyze.py
p13-regression:
	python -m uv run --frozen python -m vmarket_ai.evaluation.regression
p13-check:
	python -m uv run --frozen python evals/p13/verify.py
	python -m uv run --frozen python -m vmarket_ai.evaluation.new_questions
	python -m uv run --frozen python tools/p13_new_verify.py --artifact evals/p13/runs/new-questions-v1
	python -m uv run --frozen python -m vmarket_ai.evaluation.mapping_review verify
	python -m uv run --frozen python -m vmarket_ai.evaluation.tool_questions
	python -m uv run --frozen python tools/p13_tool_verify.py --artifact evals/p13/runs/tool-questions-v1
migrate:
	python -m uv run --frozen vmarket-ai migrate
run:
	python -m uv run --frozen vmarket-ai serve
