import anthropic
import httpx
from bs4 import BeautifulSoup
import json

client = anthropic.Anthropic(api_key="YOUR_API_KEY")

# --- Tool definitions (what Claude can "see") ---
tools = [
    {
        "name": "search_web",
        "description": "Search for a product across shopping sites. Returns a list of URLs to check.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The product search query, e.g. 'Sony WH-1000XM5 headphones buy'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch a product page and extract the price, title, and availability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the product page to fetch"
                }
            },
            "required": ["url"]
        }
    }
]