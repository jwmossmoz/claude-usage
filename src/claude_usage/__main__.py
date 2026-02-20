#!/usr/bin/env python3
"""
Claude Token Usage CLI Tool

Scans local Claude JSONL session files and displays token usage/costs
for Today, This Week, and This Month.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from claude_usage.format import render_daily_table, render_model_table, render_summary_table

# Pricing per million tokens (5-minute cache write rate; cache reads are 0.1x input).
# More-specific prefixes must come before less-specific ones — get_model_pricing()
# returns on the first match.
PRICING = {
    # Opus 4.5+ dropped to $5/$25; original Opus 4 and 4.1 remain at $15/$75.
    "claude-opus-4-6": {
        "input": 5.00,
        "output": 25.00,
        "cache_write": 6.25,
        "cache_read": 0.50,
    },
    "claude-opus-4-5": {
        "input": 5.00,
        "output": 25.00,
        "cache_write": 6.25,
        "cache_read": 0.50,
    },
    "claude-opus-4": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-5-haiku": {
        "input": 0.80,
        "output": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
}

# Requests exceeding this token count on eligible models are billed at long-context rates.
# Total input = input_tokens + cache_creation_input_tokens + cache_read_input_tokens.
_LONG_CONTEXT_THRESHOLD = 200_000

# Long-context pricing for models that support the 1M context beta.
# Cache rates use the same multipliers as standard pricing (1.25x write, 0.1x read).
_LONG_CONTEXT_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-6": {
        "input": 10.00,
        "output": 37.50,
        "cache_write": 12.50,
        "cache_read": 1.00,
    },
}


def get_model_pricing(model_name: str) -> dict[str, float] | None:
    """Get pricing for a model by matching prefix."""
    for prefix, pricing in PRICING.items():
        if model_name.startswith(prefix):
            return pricing
    return None


def parse_jsonl_file(file_path: Path) -> list[dict]:
    """Parse a JSONL file and extract assistant messages with usage."""
    messages = []

    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    # Only process assistant messages with usage data
                    if entry.get("type") == "assistant" and "message" in entry:
                        message = entry["message"]
                        if "usage" in message:
                            messages.append(
                                {
                                    "timestamp": entry.get("timestamp"),
                                    "request_id": entry.get("requestId"),
                                    "message_id": message.get("id"),
                                    "model": message.get("model"),
                                    "usage": message["usage"],
                                }
                            )
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return messages


def deduplicate_messages(messages: list[dict]) -> list[dict]:
    """
    Deduplicate messages by keeping only the last occurrence of each
    (message_id, request_id) pair, since streaming sends cumulative usage.
    """
    # Build a dict keyed by (message_id, request_id)
    unique_messages = {}

    for msg in messages:
        key = (msg["message_id"], msg["request_id"])
        unique_messages[key] = msg

    return list(unique_messages.values())


def calculate_cost(usage: dict, model: str) -> float:
    """Calculate cost for a usage entry based on model pricing."""
    pricing = get_model_pricing(model)
    if not pricing:
        return 0.0

    # Switch to long-context rates if total input exceeds 200K tokens.
    total_input = (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )
    for prefix, lc_pricing in _LONG_CONTEXT_PRICING.items():
        if model.startswith(prefix) and total_input > _LONG_CONTEXT_THRESHOLD:
            pricing = lc_pricing
            break

    cost = 0.0

    # Input tokens (non-cached)
    input_tokens = usage.get("input_tokens", 0)
    cost += (input_tokens / 1_000_000) * pricing["input"]

    # Output tokens
    output_tokens = usage.get("output_tokens", 0)
    cost += (output_tokens / 1_000_000) * pricing["output"]

    # Cache write tokens (can be at top level or nested)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    if cache_write == 0 and "cache_creation" in usage:
        # Try nested structure
        cache_creation = usage["cache_creation"]
        cache_write = cache_creation.get("ephemeral_5m_input_tokens", 0)
        cache_write += cache_creation.get("ephemeral_1h_input_tokens", 0)
    cost += (cache_write / 1_000_000) * pricing["cache_write"]

    # Cache read tokens
    cache_read = usage.get("cache_read_input_tokens", 0)
    cost += (cache_read / 1_000_000) * pricing["cache_read"]

    return cost


def categorize_by_period(messages: list[dict]) -> dict[str, list[dict]]:
    """Categorize messages by time period (today, this week, this month)."""
    now = datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Week starts on Monday
    week_start = today_start - timedelta(days=today_start.weekday())

    # Month starts on the 1st
    month_start = today_start.replace(day=1)

    categorized = {
        "today": [],
        "week": [],
        "month": [],
    }

    for msg in messages:
        timestamp_str = msg.get("timestamp")
        if not timestamp_str:
            continue

        try:
            # Parse ISO 8601 timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Convert to local timezone
            timestamp = timestamp.astimezone()

            if timestamp >= today_start:
                categorized["today"].append(msg)
            if timestamp >= week_start:
                categorized["week"].append(msg)
            if timestamp >= month_start:
                categorized["month"].append(msg)

        except Exception:
            # Skip messages with invalid timestamps
            continue

    return categorized


def categorize_by_model(messages: list[dict]) -> dict[str, list[dict]]:
    """Categorize messages by model."""
    model_buckets = {}

    for msg in messages:
        model = msg.get("model", "unknown")
        if model not in model_buckets:
            model_buckets[model] = []
        model_buckets[model].append(msg)

    return model_buckets


def categorize_by_day(messages: list[dict], days: int = 7) -> dict[str, list[dict]]:
    """Categorize messages by individual days for the last N days."""
    now = datetime.now().astimezone()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Create dict for each of the last N days
    daily_buckets = {}
    for i in range(days):
        day_start = today_start - timedelta(days=i)
        day_key = day_start.strftime("%Y-%m-%d")
        daily_buckets[day_key] = []

    for msg in messages:
        timestamp_str = msg.get("timestamp")
        if not timestamp_str:
            continue

        try:
            # Parse ISO 8601 timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            # Convert to local timezone
            timestamp = timestamp.astimezone()

            # Find which day bucket this belongs to
            for i in range(days):
                day_start = today_start - timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                if day_start <= timestamp < day_end:
                    day_key = day_start.strftime("%Y-%m-%d")
                    daily_buckets[day_key].append(msg)
                    break

        except Exception:
            # Skip messages with invalid timestamps
            continue

    return daily_buckets


def aggregate_usage(messages: list[dict]) -> tuple[dict[str, int], dict[str, float], float]:
    """
    Aggregate token usage across messages and calculate total cost.
    Returns (token_counts, token_costs, total_cost).
    """
    tokens = {
        "input": 0,
        "output": 0,
        "cache_write": 0,
        "cache_read": 0,
    }

    costs = {
        "input": 0.0,
        "output": 0.0,
        "cache": 0.0,
    }

    total_cost = 0.0

    for msg in messages:
        usage = msg["usage"]
        model = msg["model"]
        pricing = get_model_pricing(model)

        if not pricing:
            continue

        # Input tokens
        input_tokens = usage.get("input_tokens", 0)
        tokens["input"] += input_tokens
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        costs["input"] += input_cost

        # Output tokens
        output_tokens = usage.get("output_tokens", 0)
        tokens["output"] += output_tokens
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        costs["output"] += output_cost

        # Handle cache write tokens (can be at top level or nested)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        if cache_write == 0 and "cache_creation" in usage:
            cache_creation = usage["cache_creation"]
            cache_write = cache_creation.get("ephemeral_5m_input_tokens", 0)
            cache_write += cache_creation.get("ephemeral_1h_input_tokens", 0)
        tokens["cache_write"] += cache_write
        cache_write_cost = (cache_write / 1_000_000) * pricing["cache_write"]
        costs["cache"] += cache_write_cost

        # Cache read tokens
        cache_read = usage.get("cache_read_input_tokens", 0)
        tokens["cache_read"] += cache_read
        cache_read_cost = (cache_read / 1_000_000) * pricing["cache_read"]
        costs["cache"] += cache_read_cost

        total_cost += input_cost + output_cost + cache_write_cost + cache_read_cost

    return tokens, costs, total_cost


def format_number(n: int) -> str:
    """Format number with thousands separators."""
    return f"{n:,}"


def format_tokens_short(n: int) -> str:
    """Format large token counts in readable short form (K, M, B)."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def print_usage_report(
    period_name: str,
    date_range: str,
    tokens: dict[str, int],
    costs: dict[str, float],
    total_cost: float,
):
    """Print a formatted usage report for a time period."""
    total_tokens = sum(tokens.values())
    cache_total = tokens["cache_write"] + tokens["cache_read"]

    # Header
    print(f"\n┌─ {period_name} ({date_range})")
    print("│")

    # Tokens column
    print(f"│  Tokens       {format_tokens_short(tokens['input']):>8}  input")
    print(f"│               {format_tokens_short(tokens['output']):>8}  output")
    print(f"│               {format_tokens_short(cache_total):>8}  cache")
    print("│               ──────────")
    print(f"│               {format_tokens_short(total_tokens):>8}  total")
    print("│")

    # Cost breakdown
    print(f"│  Cost         ${costs['input']:>7.2f}  input")
    print(f"│               ${costs['output']:>7.2f}  output")
    print(f"│               ${costs['cache']:>7.2f}  cache")
    print("│               ──────────")
    print(f"│               ${total_cost:>7.2f}  total")
    print("└─")


def output_json(today_data: dict, week_data: dict, month_data: dict) -> str:
    """Format usage data as JSON."""
    return json.dumps(
        {
            "today": today_data,
            "week": week_data,
            "month": month_data,
        },
        indent=2,
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Track Claude API token usage and costs from local JSONL files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output data in JSON format instead of formatted table",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary view (Today/Week/Month + model breakdown)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to show in daily view (default: 7)",
    )
    args = parser.parse_args()

    # Find all JSONL files
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        print(f"Error: {claude_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    jsonl_files = list(claude_dir.glob("**/*.jsonl"))

    if not jsonl_files:
        print("No JSONL files found in ~/.claude/projects/", file=sys.stderr)
        sys.exit(1)

    # Parse all files
    all_messages = []
    for file_path in jsonl_files:
        messages = parse_jsonl_file(file_path)
        all_messages.extend(messages)

    # Deduplicate
    all_messages = deduplicate_messages(all_messages)

    if not all_messages:
        print("No usage data found in JSONL files", file=sys.stderr)
        sys.exit(1)

    now = datetime.now().astimezone()

    # Check which view to show
    if args.summary:
        # Categorize by period for summary view
        categorized = categorize_by_period(all_messages)
        today_tokens, today_costs, today_total = aggregate_usage(categorized["today"])
        week_tokens, week_costs, week_total = aggregate_usage(categorized["week"])
        month_tokens, month_costs, month_total = aggregate_usage(categorized["month"])
        week_start = now - timedelta(days=now.weekday())

        # Also get model breakdown for summary
        model_buckets = categorize_by_model(all_messages)
    else:
        # Categorize by day for daily view
        daily_buckets = categorize_by_day(all_messages, args.days)

    # Output as JSON if requested
    if args.json:
        cache_total_today = today_tokens["cache_write"] + today_tokens["cache_read"]
        cache_total_week = week_tokens["cache_write"] + week_tokens["cache_read"]
        cache_total_month = month_tokens["cache_write"] + month_tokens["cache_read"]

        output = {
            "today": {
                "date": now.strftime("%Y-%m-%d"),
                "tokens": {
                    "input": today_tokens["input"],
                    "output": today_tokens["output"],
                    "cache": cache_total_today,
                    "total": sum(today_tokens.values()),
                },
                "costs": {
                    "input": round(today_costs["input"], 2),
                    "output": round(today_costs["output"], 2),
                    "cache": round(today_costs["cache"], 2),
                    "total": round(today_total, 2),
                },
            },
            "week": {
                "date_range": f"{week_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}",
                "tokens": {
                    "input": week_tokens["input"],
                    "output": week_tokens["output"],
                    "cache": cache_total_week,
                    "total": sum(week_tokens.values()),
                },
                "costs": {
                    "input": round(week_costs["input"], 2),
                    "output": round(week_costs["output"], 2),
                    "cache": round(week_costs["cache"], 2),
                    "total": round(week_total, 2),
                },
            },
            "month": {
                "date_range": now.strftime("%B %Y"),
                "tokens": {
                    "input": month_tokens["input"],
                    "output": month_tokens["output"],
                    "cache": cache_total_month,
                    "total": sum(month_tokens.values()),
                },
                "costs": {
                    "input": round(month_costs["input"], 2),
                    "output": round(month_costs["output"], 2),
                    "cache": round(month_costs["cache"], 2),
                    "total": round(month_total, 2),
                },
            },
        }
        print(json.dumps(output, indent=2))
        return

    # Prepare data for output
    if args.summary:
        # Prepare summary data (Today/Week/Month)
        cache_total_today = today_tokens["cache_write"] + today_tokens["cache_read"]
        cache_total_week = week_tokens["cache_write"] + week_tokens["cache_read"]
        cache_total_month = month_tokens["cache_write"] + month_tokens["cache_read"]

        today_data = {
            "date_label": now.strftime("%b %d, %Y"),
            "tokens": {
                "input": today_tokens["input"],
                "output": today_tokens["output"],
                "cache": cache_total_today,
                "total": sum(today_tokens.values()),
            },
            "costs": {
                "input": today_costs["input"],
                "output": today_costs["output"],
                "cache": today_costs["cache"],
                "total": today_total,
            },
        }

        week_data = {
            "date_label": f"{week_start.strftime('%b %d')} - {now.strftime('%b %d')}",
            "tokens": {
                "input": week_tokens["input"],
                "output": week_tokens["output"],
                "cache": cache_total_week,
                "total": sum(week_tokens.values()),
            },
            "costs": {
                "input": week_costs["input"],
                "output": week_costs["output"],
                "cache": week_costs["cache"],
                "total": week_total,
            },
        }

        month_data = {
            "date_label": now.strftime("%B %Y"),
            "tokens": {
                "input": month_tokens["input"],
                "output": month_tokens["output"],
                "cache": cache_total_month,
                "total": sum(month_tokens.values()),
            },
            "costs": {
                "input": month_costs["input"],
                "output": month_costs["output"],
                "cache": month_costs["cache"],
                "total": month_total,
            },
        }

        # Prepare model breakdown data
        model_data = []
        for model_name, messages in sorted(model_buckets.items()):
            model_tokens, model_costs, model_total = aggregate_usage(messages)
            cache_total = model_tokens["cache_write"] + model_tokens["cache_read"]

            model_data.append(
                {
                    "model_name": model_name,
                    "message_count": len(messages),
                    "tokens": {
                        "input": model_tokens["input"],
                        "output": model_tokens["output"],
                        "cache": cache_total,
                        "total": sum(model_tokens.values()),
                    },
                    "costs": {
                        "input": model_costs["input"],
                        "output": model_costs["output"],
                        "cache": model_costs["cache"],
                        "total": model_total,
                    },
                }
            )

        # Render both summary and model tables
        render_summary_table(today_data, week_data, month_data)
        print()  # Add spacing between tables
        render_model_table(model_data)
    else:
        # Prepare daily data
        daily_data = []
        for i in range(args.days - 1, -1, -1):  # Reverse to show oldest first
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_key = day_start.strftime("%Y-%m-%d")

            if day_key in daily_buckets:
                day_tokens, day_costs, day_total = aggregate_usage(daily_buckets[day_key])
                cache_total_day = day_tokens["cache_write"] + day_tokens["cache_read"]

                daily_data.append(
                    {
                        "date_label": day_start.strftime("%a, %b %d"),
                        "tokens": {
                            "input": day_tokens["input"],
                            "output": day_tokens["output"],
                            "cache": cache_total_day,
                            "total": sum(day_tokens.values()),
                        },
                        "costs": {
                            "input": day_costs["input"],
                            "output": day_costs["output"],
                            "cache": day_costs["cache"],
                            "total": day_total,
                        },
                    }
                )
            else:
                # No data for this day, add zeros
                daily_data.append(
                    {
                        "date_label": day_start.strftime("%a, %b %d"),
                        "tokens": {"input": 0, "output": 0, "cache": 0, "total": 0},
                        "costs": {"input": 0.0, "output": 0.0, "cache": 0.0, "total": 0.0},
                    }
                )

        render_daily_table(daily_data)


if __name__ == "__main__":
    main()
