.PHONY: dev lint format test run clean

# Install all dependencies
dev:
	uv sync --all-groups

# Run linter and type checker
lint:
	uv run ruff check .
	uv run ty check src/

# Format code
format:
	uv run ruff format .

# Run tests
test:
	uv run pytest

# Run the tool
run:
	uv run claude-usage

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
