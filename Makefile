sync:
	uv sync --group dev

test:
	uv run pytest tests/

format:
	uv run ruff format src/ tests/

lint:
	uv run ruff check --fix src/ tests/

check: format lint test
