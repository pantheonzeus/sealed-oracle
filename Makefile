.PHONY: check lint test variants image results

check: lint test variants

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest -q

variants:
	uv run sealed-oracle check-variants

image:
	docker build -t sdlc-eval-kit:0.1 kit/docker/

results:
	uv run sealed-oracle results
