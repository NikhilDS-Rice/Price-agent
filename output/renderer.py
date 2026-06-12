"""
Output renderer — prints the agent's final result in a clean terminal format.
Also handles saving results to JSON for later use.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def render_result(run: dict) -> None:
    """Pretty-print the agent's final answer to the terminal."""
    console.print()

    answer = run.get("final_answer", "")
    if not answer:
        console.print("[red]No result returned by agent.[/red]")
        return

    console.print(Panel(
        answer,
        title=f"[bold]Results: {run['product']}[/bold]",
        border_style="green",
        padding=(1, 2),
    ))

    # Print a stats footer
    n = run.get("total_tool_calls", 0)
    console.print(f"\n[dim]  {n} tool calls made[/dim]")


def render_comparison_table(comparison: dict) -> None:
    """
    If compare_and_rank was called, render its output as a Rich table.
    This is called separately from render_result to show a structured view.
    """
    if not comparison:
        return

    ranked = comparison.get("ranked_results", [])
    if not ranked:
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
        title=f"Price comparison: {comparison.get('product_name', '')}",
        title_style="bold",
        pad_edge=False,
        show_edge=False,
    )

    table.add_column("Rank", style="dim", width=5)
    table.add_column("Store", min_width=12)
    table.add_column("Price", min_width=10, justify="right")
    table.add_column("Rating", min_width=14)
    table.add_column("Shipping", min_width=16)
    table.add_column("Stock", width=8)

    for r in ranked:
        rank_str = "★ 1" if r.get("is_best_deal") else str(r.get("rank") or "—")
        store = r.get("store", "")
        price = r.get("price", "N/A")
        rating = r.get("rating", "—")[:20]
        shipping = (r.get("shipping") or "—")[:24]
        in_stock = "[green]Yes[/green]" if r.get("in_stock") else "[red]No[/red]"

        style = "bold green" if r.get("is_best_deal") else ""

        table.add_row(
            Text(rank_str, style=style),
            Text(store, style=style),
            Text(price, style=style),
            rating,
            shipping,
            in_stock,
        )

    console.print()
    console.print(table)

    best = comparison.get("best_deal", {})
    price_range = comparison.get("price_range", "")
    if best and price_range:
        console.print(
            f"\n  [bold green]Best deal:[/bold green] {best.get('store')} "
            f"at [bold]{best.get('price')}[/bold]  |  "
            f"Price range across stores: {price_range}"
        )


def save_result(run: dict, output_dir: str = "output") -> Path:
    """Save the full run to a JSON file for inspection or future use."""
    Path(output_dir).mkdir(exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", run["product"]).strip().replace(" ", "_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"{slug}_{ts}.json"
    with open(path, "w") as f:
        json.dump(run, f, indent=2, default=str)
    return path


def extract_comparison_from_run(run: dict) -> dict:
    """Pull the compare_and_rank result out of tool call history."""
    for call in reversed(run.get("tool_calls", [])):
        if call["tool"] == "compare_and_rank":
            return call.get("output", {})
    return {}
