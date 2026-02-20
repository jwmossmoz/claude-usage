# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make dev      # Install dependencies: uv sync --all-groups
make lint     # ruff check + ty check
make format   # ruff format
make test     # pytest
make run      # Run the CLI
```

Run a single test:
```bash
uv run pytest tests/path/to/test.py::test_name -q
```

## Architecture

The tool reads Claude session JSONL files from `~/.claude/projects/**/*.jsonl` and aggregates token usage into time-period and model breakdowns.

**Entry point**: `src/claude_usage/__main__.py` — all CLI logic lives here.

**Data pipeline** (all in `__main__.py`):
1. `parse_jsonl_file()` — extracts assistant messages with `usage` fields from JSONL
2. `deduplicate_messages()` — streaming responses emit cumulative counts; keeps the last occurrence per `uuid`
3. `calculate_cost()` — applies per-model pricing (input, output, cache write, cache read tokens)
4. `categorize_by_period()` / `categorize_by_day()` — bins messages into Today/Week/Month or daily buckets
5. `aggregate_usage()` — sums token counts and costs across a set of messages

**Rendering**: `src/claude_usage/format.py` — Rich-based table formatters. `format_tokens()` converts raw counts to K/M shorthand.

**Pricing**: Hard-coded constants at the top of `__main__.py` for four models (Opus 4, Sonnet 4, Sonnet 3.5, Haiku 3.5).

**CLI flags**: `--json`, `--summary`, `--days N` (default 7 for daily view).

## Notes

- No test suite exists yet (`tests/` directory missing); pytest is configured in `pyproject.toml`
- No CI/CD pipelines configured
- Python ≥3.11 required; use `uv` for all dependency management
