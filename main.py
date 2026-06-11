#!/usr/bin/env python3
"""
Price Comparison Agent — CLI entrypoint

Usage:
  python main.py "Sony WH-1000XM5 headphones"
  python main.py "iPhone 15 Pro 256GB" --verbose
  python main.py "Nintendo Switch OLED" --save
  python main.py --help
"""

import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()  # loads .env file if present

from core.agent import run_agent
from output.renderer import render_result, render_comparison_table, save_result, extract_comparison_from_run

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered price comparison agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Sony WH-1000XM5"
  python main.py "MacBook Air M3 15 inch" --verbose
  python main.py "Dyson V15 vacuum" --save
        """
    )
    parser.add_argument(
        "product",
        nargs="?",
        help="Product to search for (wrap in quotes if it contains spaces)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show raw tool inputs and outputs"
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save full results to a JSON file in ./output/"
    )

    args = parser.parse_args()

    if not args.product:
        console.print("[bold]Price Comparison Agent[/bold]")
        console.print("Usage: python main.py \"product name here\"")
        console.print("\nExample: python main.py \"Sony WH-1000XM5 headphones\"")
        sys.exit(0)

    try:
        run = run_agent(args.product, verbose=args.verbose)
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("\nMake sure your .env file has ANTHROPIC_API_KEY and SERP_API_KEY set.")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)

    # Show the final answer
    render_result(run)

    # Also show the structured comparison table if available
    comparison = extract_comparison_from_run(run)
    if comparison:
        render_comparison_table(comparison)

    # Optionally save
    if args.save:
        path = save_result(run)
        console.print(f"\n[dim]Results saved to {path}[/dim]")


if __name__ == "__main__":
    main()
