"""
Tool schemas — the JSON descriptions Claude reads to decide what to call.
Kept separate from implementations so they're easy to read and modify.
"""

TOOL_DEFINITIONS = [
    {
        "name": "search_products",
        "description": (
            "Search for a product across the web using SerpAPI Google Shopping. "
            "Returns a list of results with store name, price, link, and rating. "
            "Use this first to discover where a product is sold and at what prices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The product search query. Be specific — include brand, "
                        "model number, and key specs. "
                        "Example: 'Sony WH-1000XM5 wireless headphones'"
                    )
                },
                "num_results": {
                    "type": "integer",
                    "description": "How many results to return (max 10). Default 5.",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_product_page",
        "description": (
            "Fetch a specific product page URL and extract detailed info: "
            "exact price, availability, shipping cost, seller details, and specs. "
            "Use this to verify and enrich results from search_products."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full product page URL to fetch and parse."
                },
                "store_name": {
                    "type": "string",
                    "description": "The retailer name, e.g. 'Amazon', 'Best Buy'. Used for context."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "compare_and_rank",
        "description": (
            "Takes all collected product results and produces a structured comparison. "
            "Call this as the FINAL step after you have fetched prices from multiple stores. "
            "Returns a ranked list with the best deal highlighted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "The clean product name to display in the comparison."
                },
                "results": {
                    "type": "array",
                    "description": "Array of product result objects collected from other tools.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "store": {"type": "string"},
                            "price": {"type": "string"},
                            "original_price": {"type": "string"},
                            "url": {"type": "string"},
                            "rating": {"type": "string"},
                            "shipping": {"type": "string"},
                            "in_stock": {"type": "boolean"},
                            "notes": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["product_name", "results"]
        }
    },
    {
        "name": "search_web",
        "description": (
            "General-purpose web search (not shopping-specific). "
            "Use this to find reviews, comparisons, or recent news about a product "
            "that could inform the recommendation. Optional — does not replace "
            "search_products or compare_and_rank."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The web search query, e.g. 'Sony WH-1000XM5 review' "
                        "or 'best wireless headphones 2026'."
                    )
                },
                "num_results": {
                    "type": "integer",
                    "description": "How many results to return (max 10). Default 5.",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]
