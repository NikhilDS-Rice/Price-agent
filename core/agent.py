"""
Agent core — the main loop that drives Claude through search, fetch, and compare.
"""

import os
import json
import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

from tools.schemas import TOOL_DEFINITIONS
from tools.router import run_tool

console = Console()

SYSTEM_PROMPT = """You are a price comparison agent. Your goal is to find the best deal for a product.

Follow this exact workflow:
1. Call search_products with a precise query to find listings across stores
2. Call fetch_product_page on the 3-5 most promising URLs to get verified prices and details
   - Skip blocked pages (403 errors) — the price from search results is still useful
   - Prioritize major retailers: Amazon, Best Buy, Walmart, Target, Costco
3. Call compare_and_rank with ALL collected results to produce the final comparison
4. After compare_and_rank returns, write a clear summary for the user:
   - Lead with the best deal (store + price + why it's the best)
   - List all options in a simple table
   - Note any caveats (stock, shipping costs, open-box options)
   - Keep it concise — users want to act quickly

Important rules:
- Always call compare_and_rank as your final tool call before writing the summary
- If a page is blocked, don't retry it — move on
- If search returns no results, try a slightly different query (more/less specific)
- Do not make up prices — only report what tools return
"""


def run_agent(product: str, verbose: bool = False) -> dict:
    """
    Runs the price comparison agent for a given product query.
    Returns the full run summary including all tool calls and final result.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=api_key)
    max_tool_calls = int(os.getenv("MAX_TOOL_CALLS", "20"))

    messages = [{"role": "user", "content": f'Find the best price for: "{product}"'}]

    tool_call_count = 0
    all_tool_calls = []
    final_text = ""

    console.print()
    console.print(Panel(
        f"[bold]Searching for:[/bold] {product}",
        border_style="dim",
        padding=(0, 1)
    ))

    while tool_call_count < max_tool_calls:
        with Live(Spinner("dots", text=" Thinking..."), console=console, refresh_per_second=10):
            response = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    final_text = block.text
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_call_count += 1
                    console.print(f"\n[bold cyan]▸ {block.name}[/bold cyan]", end="")
                    if verbose:
                        console.print(f"\n  [dim]{json.dumps(block.input, indent=2)}[/dim]")
                    else:
                        key_arg = (
                            block.input.get("query")
                            or block.input.get("url", "")[:60]
                            or block.input.get("product_name", "")
                        )
                        console.print(f" [dim]{key_arg}[/dim]")

                    with Live(Spinner("dots2", text=" Running..."), console=console, refresh_per_second=10):
                        result_str = run_tool(block.name, block.input)

                    result_data = json.loads(result_str)
                    all_tool_calls.append({
                        "tool": block.name,
                        "input": block.input,
                        "output": result_data,
                    })

                    if verbose:
                        console.print(f"  [dim]{result_str[:300]}...[/dim]")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            console.print(f"[yellow]Unexpected stop_reason: {response.stop_reason}[/yellow]")
            break

    if tool_call_count >= max_tool_calls:
        console.print(f"[yellow]Hit max tool call limit ({max_tool_calls})[/yellow]")

    return {
        "product": product,
        "final_answer": final_text,
        "tool_calls": all_tool_calls,
        "total_tool_calls": tool_call_count,
    }
