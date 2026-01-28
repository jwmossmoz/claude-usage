# Claude Token Usage

Track Claude API token usage and costs from local JSONL session files.

## Overview

This tool scans local Claude JSONL session files (`~/.claude/projects/**/*.jsonl`) and displays token usage and costs for:
- Today
- This Week
- This Month

> **Inspired by [CodexBar](https://github.com/steipete/CodexBar)** 🎉
> Shoutout to [Peter Steinberger](https://github.com/steipete) for creating CodexBar, the awesome macOS menu bar app that tracks Claude Code and OpenAI Codex usage. This CLI tool brings similar functionality to the command line for detailed token analysis!

## Installation

```bash
# Clone the repository
git clone https://github.com/jwmoss/claude-usage.git
cd claude-usage

# Install with uv
uv sync

# Or install as a tool
uvx install .
```

## Usage

```bash
# Default: Show daily breakdown for last 7 days
uv run claude-usage

# Show more days (daily view)
uv run claude-usage --days 14

# Show summary view (Today/Week/Month + model breakdown)
uv run claude-usage --summary

# Output as JSON
uv run claude-usage --json

# Show help
uv run claude-usage --help
```

## Output Examples

### Daily Breakdown (default)

```
                 Claude Token Usage - Last 7 Days
┏━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Date        ┃ Input ┃ Output ┃  Cache ┃ Total Tokens ┃    Cost ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ Mon, Jan 20 │  1.2K │    345 │   5.1K │         6.6K │   $0.12 │
│ Tue, Jan 21 │  2.3K │    567 │   8.2K │        11.1K │   $0.23 │
│ Wed, Jan 22 │  1.8K │    234 │   3.4K │         5.4K │   $0.09 │
│ Thu, Jan 23 │  3.1K │    678 │  12.5K │        16.3K │   $0.31 │
│ Fri, Jan 24 │  2.7K │    456 │   9.8K │        13.0K │   $0.25 │
│ Sat, Jan 25 │     0 │      0 │      0 │            0 │   $0.00 │
│ Sun, Jan 26 │     0 │      0 │      0 │            0 │   $0.00 │
├─────────────┼───────┼────────┼────────┼──────────────┼─────────┤
│ Total       │ 11.1K │   2.3K │  39.0K │        52.4K │   $1.00 │
└─────────────┴───────┴────────┴────────┴──────────────┴─────────┘
```

### Summary View (`--summary`)

The summary view shows two tables:

**1. Time Period Summary:**
```
                      Claude Token Usage - Summary
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Period          ┃  Input ┃ Output ┃  Cache ┃ Total Tokens ┃     Cost ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ Today           │  3.1K  │    678 │  12.5K │        16.3K │    $0.31 │
│ Jan 26, 2026    │        │        │        │              │          │
│ This Week       │ 11.1K  │   2.3K │  39.0K │        52.4K │    $1.00 │
│ Jan 20 - Jan 26 │        │        │        │              │          │
│ This Month      │ 23.5K  │   5.7K │  89.2K │       118.4K │    $2.15 │
│ January 2026    │        │        │        │              │          │
└─────────────────┴────────┴────────┴────────┴──────────────┴──────────┘
```

**2. Model Breakdown:**

```
                         Claude Token Usage - By Model
┏━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Model        ┃ Messages ┃  Input ┃ Output ┃  Cache ┃ Total Tokens ┃     Cost ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ claude-opus… │       12 │   8.2K │   2.1K │  34.5K │        44.8K │    $1.15 │
│ claude-sonn… │       38 │  15.3K │   3.6K │  54.7K │        73.6K │    $1.00 │
│ claude-haik… │        5 │      0 │      0 │      0 │            0 │    $0.00 │
├──────────────┼──────────┼────────┼────────┼────────┼──────────────┼──────────┤
│ Total        │       55 │  23.5K │   5.7K │  89.2K │       118.4K │    $2.15 │
└──────────────┴──────────┴────────┴────────┴────────┴──────────────┴──────────┘
```

The model breakdown shows:
- Which Claude models you're using (Opus 4, Sonnet 4, Haiku 3.5, etc.)
- How many messages each model handled
- Token usage breakdown per model
- Cost per model

**Perfect for:** High-level overview of your usage patterns and costs across different time periods and models.

### JSON Format (`--json`)

```json
{
  "today": {
    "date": "2026-01-26",
    "tokens": {
      "input": 3100,
      "output": 678,
      "cache": 12500,
      "total": 16278
    },
    "costs": {
      "input": 0.09,
      "output": 0.10,
      "cache": 0.12,
      "total": 0.31
    }
  },
  "week": {
    "date_range": "2026-01-20 to 2026-01-26",
    "tokens": {
      "input": 11100,
      "output": 2300,
      "cache": 39000,
      "total": 52400
    },
    "costs": {
      "input": 0.33,
      "output": 0.35,
      "cache": 0.32,
      "total": 1.00
    }
  }
}
```

## Features

- **Daily breakdown** - See usage for each of the last 7 days (default) with totals
- **Summary view** - Today/Week/Month summary + model breakdown with `--summary`
- **Customizable range** - Show any number of days with `--days N` (works with daily view)
- **Rich table output** - Clean, professional tables using the Rich library (like [optionctl](https://github.com/jwmoss/optionctl))
- **JSON export** - Machine-readable output for scripting and automation
- **Smart number formatting** - Displays large numbers as 52.1M instead of 52,104,345
- **Automatic deduplication** - Handles streaming responses correctly
- **Model-aware pricing** - Accurately calculates costs based on model type (see Pricing section below)
- **Timezone aware** - Properly handles local vs UTC timestamps

## Pricing

The tool calculates costs using [official Claude API pricing](https://claude.com/pricing#api) (per million tokens):

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| Claude Opus 4 | $15.00 | $75.00 | $18.75 | $1.50 |
| Claude Sonnet 4 | $3.00 | $15.00 | $3.75 | $0.30 |
| Claude 3.5 Sonnet | $3.00 | $15.00 | $3.75 | $0.30 |
| Claude 3.5 Haiku | $0.80 | $4.00 | $1.00 | $0.08 |

Costs are calculated by:
1. Reading token usage from JSONL session files
2. Identifying the model used for each message
3. Applying model-specific pricing to input, output, cache write, and cache read tokens

**Want to see usage by model?** Use `claude-usage --summary` to see both time-based summary and model breakdown.

## Development

```bash
# Install dev dependencies
uv sync --all-groups

# Run linter
uv run ruff check .

# Format code
uv run ruff format .

# Run type checker
uv run ty check src/

# Run tests
uv run pytest
```

## License

MIT
