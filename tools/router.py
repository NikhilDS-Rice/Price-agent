"""
Tool router — maps Claude's tool_use calls to Python implementations.
"""

import json
from tools.implementations import search_products, fetch_product_page, compare_and_rank, search_web


def run_tool(name: str, inputs: dict) -> str:
    """
    Executes the named tool and returns the result as a JSON string
    (Claude expects tool results as strings).
    """
    try:
        if name == "search_products":
            result = search_products(**inputs)
        elif name == "fetch_product_page":
            result = fetch_product_page(**inputs)
        elif name == "compare_and_rank":
            result = compare_and_rank(**inputs)
        elif name == "search_web":
            result = search_web(**inputs)
        else:
            result = {"error": f"Unknown tool: {name}"}
    except TypeError as e:
        result = {"error": f"Tool called with wrong arguments: {e}"}
    except Exception as e:
        result = {"error": f"Tool execution failed: {e}"}

    return json.dumps(result, default=str)
