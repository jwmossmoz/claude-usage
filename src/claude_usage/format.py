"""Output formatting for claude-usage."""

from rich.console import Console
from rich.table import Table

console = Console()


def format_tokens(n: int) -> str:
    """Format token counts with K/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,}"


def render_daily_table(daily_data: list[dict]) -> None:
    """Render daily breakdown as a rich table."""
    table = Table(title="Claude Token Usage - Last 7 Days", show_lines=False)

    table.add_column("Date", style="cyan")
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="green")
    table.add_column("Cache", justify="right", style="green")
    table.add_column("Total Tokens", justify="right", style="bold cyan")
    table.add_column("Cost", justify="right", style="bold yellow")

    total_input = 0
    total_output = 0
    total_cache = 0
    total_tokens_sum = 0
    total_cost_sum = 0.0

    for day in daily_data:
        table.add_row(
            day["date_label"],
            format_tokens(day["tokens"]["input"]),
            format_tokens(day["tokens"]["output"]),
            format_tokens(day["tokens"]["cache"]),
            format_tokens(day["tokens"]["total"]),
            f"${day['costs']['total']:.2f}",
        )
        total_input += day["tokens"]["input"]
        total_output += day["tokens"]["output"]
        total_cache += day["tokens"]["cache"]
        total_tokens_sum += day["tokens"]["total"]
        total_cost_sum += day["costs"]["total"]

    # Add total row
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{format_tokens(total_input)}[/bold]",
        f"[bold]{format_tokens(total_output)}[/bold]",
        f"[bold]{format_tokens(total_cache)}[/bold]",
        f"[bold]{format_tokens(total_tokens_sum)}[/bold]",
        f"[bold]${total_cost_sum:.2f}[/bold]",
    )

    console.print(table)


def render_summary_table(
    today_data: dict,
    week_data: dict,
    month_data: dict,
) -> None:
    """Render summary usage data as a rich table."""
    table = Table(title="Claude Token Usage - Summary", show_lines=False)

    table.add_column("Period", style="cyan")
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="green")
    table.add_column("Cache", justify="right", style="green")
    table.add_column("Total Tokens", justify="right", style="bold cyan")
    table.add_column("Cost", justify="right", style="bold yellow")

    # Today row
    table.add_row(
        f"Today\n{today_data['date_label']}",
        format_tokens(today_data["tokens"]["input"]),
        format_tokens(today_data["tokens"]["output"]),
        format_tokens(today_data["tokens"]["cache"]),
        format_tokens(today_data["tokens"]["total"]),
        f"${today_data['costs']['total']:.2f}",
    )

    # This week row
    table.add_row(
        f"This Week\n{week_data['date_label']}",
        format_tokens(week_data["tokens"]["input"]),
        format_tokens(week_data["tokens"]["output"]),
        format_tokens(week_data["tokens"]["cache"]),
        format_tokens(week_data["tokens"]["total"]),
        f"${week_data['costs']['total']:.2f}",
    )

    # This month row
    table.add_row(
        f"This Month\n{month_data['date_label']}",
        format_tokens(month_data["tokens"]["input"]),
        format_tokens(month_data["tokens"]["output"]),
        format_tokens(month_data["tokens"]["cache"]),
        format_tokens(month_data["tokens"]["total"]),
        f"${month_data['costs']['total']:.2f}",
    )

    console.print(table)


def render_model_table(model_data: list[dict]) -> None:
    """Render usage breakdown by model as a rich table."""
    table = Table(title="Claude Token Usage - By Model", show_lines=False)

    table.add_column("Model", style="cyan")
    table.add_column("Messages", justify="right", style="blue")
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="green")
    table.add_column("Cache", justify="right", style="green")
    table.add_column("Total Tokens", justify="right", style="bold cyan")
    table.add_column("Cost", justify="right", style="bold yellow")

    total_messages = 0
    total_input = 0
    total_output = 0
    total_cache = 0
    total_tokens_sum = 0
    total_cost_sum = 0.0

    for model in model_data:
        table.add_row(
            model["model_name"],
            f"{model['message_count']:,}",
            format_tokens(model["tokens"]["input"]),
            format_tokens(model["tokens"]["output"]),
            format_tokens(model["tokens"]["cache"]),
            format_tokens(model["tokens"]["total"]),
            f"${model['costs']['total']:.2f}",
        )
        total_messages += model["message_count"]
        total_input += model["tokens"]["input"]
        total_output += model["tokens"]["output"]
        total_cache += model["tokens"]["cache"]
        total_tokens_sum += model["tokens"]["total"]
        total_cost_sum += model["costs"]["total"]

    # Add total row
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_messages:,}[/bold]",
        f"[bold]{format_tokens(total_input)}[/bold]",
        f"[bold]{format_tokens(total_output)}[/bold]",
        f"[bold]{format_tokens(total_cache)}[/bold]",
        f"[bold]{format_tokens(total_tokens_sum)}[/bold]",
        f"[bold]${total_cost_sum:.2f}[/bold]",
    )

    console.print(table)
