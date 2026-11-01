.PHONY: install lint typecheck test contracts dataset-check ingestion-demo retrieval-eval-check mapping-eval-check migrate run
install:
	python -m uv sync --locked
lint:
	python -m uv run --frozen ruff check src tests migrations tools/validate_contracts.py tools/p09_local_smoke.py tools/p10_local_smoke.py tools/p10_checks.py tools/p11_local_smoke.py tools/p11_checks.py tools/p11_proxy.py evals/retrieval/analyze.py evals/mapping/analyze.py
	python -m uv run --frozen ruff format --check src tests migrations tools/validate_contracts.py tools/p09_local_smoke.py tools/p10_local_smoke.py tools/p10_checks.py tools/p11_local_smoke.py tools/p11_checks.py tools/p11_proxy.py evals/retrieval/analyze.py evals/mapping/analyze.py
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
migrate:
	python -m uv run --frozen vmarket-ai migrate
run:
	python -m uv run --frozen vmarket-ai serve
