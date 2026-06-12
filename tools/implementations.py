"""
Tool implementations — the actual Python that runs when Claude calls a tool.
"""

import os
import re
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS_PER_SEARCH", "5"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Tool 1: search_products
# ---------------------------------------------------------------------------

def search_products(query: str, num_results: int = 5) -> dict:
    """
    Calls SerpAPI Google Shopping to find real product listings.
    Returns structured results with store, price, rating, and URL.
    """
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        return {"error": "SERP_API_KEY not set in environment."}

    num_results = min(num_results, MAX_RESULTS)
    console.print(f"  [dim]→ SerpAPI search: [italic]{query}[/italic][/dim]")

    try:
        resp = httpx.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_shopping",
                "q": query,
                "num": num_results,
                "api_key": api_key,
                "gl": "us",
                "hl": "en",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.TimeoutException:
        return {"error": "SerpAPI request timed out."}
    except httpx.HTTPStatusError as e:
        return {"error": f"SerpAPI returned HTTP {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

    shopping_results = data.get("shopping_results", [])
    if not shopping_results:
        # Fall back to organic results if no shopping tab
        shopping_results = data.get("organic_results", [])

    if not shopping_results:
        return {"error": "No results found. Try a more specific query.", "raw_query": query}

    results = []
    for item in shopping_results[:num_results]:
        results.append({
            "store": item.get("source", "Unknown"),
            "title": item.get("title", ""),
            "price": item.get("price", "N/A"),
            "original_price": item.get("extracted_price", None),
            "rating": _fmt_rating(item),
            "reviews": item.get("reviews", None),
            "url": item.get("link") or item.get("product_link", ""),
            "thumbnail": item.get("thumbnail", ""),
            "tag": item.get("tag", ""),
            "shipping": item.get("shipping", ""),
            "in_stock": True,  # assume in stock if listed; fetch_page will verify
        })

    console.print(f"  [dim]→ Found {len(results)} results[/dim]")
    return {"results": results, "total_found": len(results)}


def _fmt_rating(item: dict) -> str:
    rating = item.get("rating")
    reviews = item.get("reviews")
    if rating and reviews:
        return f"{rating}/5 ({reviews:,} reviews)"
    elif rating:
        return f"{rating}/5"
    return "No rating"


# ---------------------------------------------------------------------------
# Tool 2: fetch_product_page
# ---------------------------------------------------------------------------

def fetch_product_page(url: str, store_name: str = "") -> dict:
    """
    Fetches a product page and extracts price, availability, and details.
    Uses heuristic CSS selectors tuned for major retailers.
    Falls back to generic extraction for unknown sites.
    """
    console.print(f"  [dim]→ Fetching: [italic]{url[:70]}...[/italic][/dim]")

    if not url or not url.startswith("http"):
        return {"error": f"Invalid URL: {url}"}

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.TimeoutException:
        return {"error": "Page request timed out.", "url": url, "store": store_name}
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            return {
                "error": "Access blocked by retailer (anti-bot). Price from search results is reliable.",
                "url": url,
                "store": store_name,
                "blocked": True,
            }
        return {"error": f"HTTP {e.response.status_code}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}

    soup = BeautifulSoup(resp.text, "html.parser")
    domain = _domain(url)

    if "amazon" in domain:
        return _parse_amazon(soup, url)
    elif "bestbuy" in domain:
        return _parse_bestbuy(soup, url)
    elif "walmart" in domain:
        return _parse_walmart(soup, url)
    elif "target" in domain:
        return _parse_target(soup, url)
    else:
        return _parse_generic(soup, url, store_name)


def _domain(url: str) -> str:
    try:
        return url.split("/")[2].lower()
    except Exception:
        return ""


def _extract_price(text: str) -> str:
    """Pull first price-like string from text."""
    if not text:
        return ""
    match = re.search(r"\$[\d,]+\.?\d{0,2}", text)
    return match.group(0) if match else text.strip()


def _parse_amazon(soup: BeautifulSoup, url: str) -> dict:
    title = soup.select_one("#productTitle")
    price_whole = soup.select_one(".a-price-whole")
    price_fraction = soup.select_one(".a-price-fraction")
    price_str = ""
    if price_whole:
        price_str = "$" + price_whole.get_text(strip=True).rstrip(".")
        if price_fraction:
            price_str += "." + price_fraction.get_text(strip=True)

    availability = soup.select_one("#availability")
    rating = soup.select_one(".a-icon-star .a-icon-alt") or soup.select_one("#acrPopover")
    review_count = soup.select_one("#acrCustomerReviewText")
    shipping = soup.select_one("#mir-layout-DELIVERY_BLOCK")

    return {
        "store": "Amazon",
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "price": price_str or "See page",
        "in_stock": "In Stock" in (availability.get_text() if availability else ""),
        "availability": availability.get_text(strip=True) if availability else "Unknown",
        "rating": rating.get_text(strip=True) if rating else "",
        "reviews": review_count.get_text(strip=True) if review_count else "",
        "shipping": shipping.get_text(strip=True)[:100] if shipping else "",
    }


def _parse_bestbuy(soup: BeautifulSoup, url: str) -> dict:
    title = soup.select_one(".sku-title h1")
    price = soup.select_one(".priceView-customer-price span")
    availability = soup.select_one(".fulfillment-fulfillment-summary")
    rating = soup.select_one(".ugc-ratings-reviews .c-review-average")

    return {
        "store": "Best Buy",
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "price": _extract_price(price.get_text() if price else ""),
        "in_stock": "Add to Cart" in soup.get_text(),
        "availability": availability.get_text(strip=True)[:80] if availability else "Check site",
        "rating": rating.get_text(strip=True) if rating else "",
        "shipping": "Free shipping available" if "free shipping" in soup.get_text().lower() else "",
    }


def _parse_walmart(soup: BeautifulSoup, url: str) -> dict:
    title = soup.select_one('[itemprop="name"]') or soup.select_one("h1")
    price = soup.select_one('[itemprop="price"]') or soup.select_one(".price-characteristic")

    price_str = ""
    if price:
        price_str = price.get("content") or price.get_text(strip=True)
        if price_str and not price_str.startswith("$"):
            price_str = "$" + price_str

    return {
        "store": "Walmart",
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "price": price_str or "See page",
        "in_stock": "Add to cart" in soup.get_text().lower(),
        "shipping": "Free shipping" if "free shipping" in soup.get_text().lower() else "",
    }


def _parse_target(soup: BeautifulSoup, url: str) -> dict:
    title = soup.select_one("h1[data-test='product-title']") or soup.select_one("h1")
    price = soup.select_one("[data-test='product-price']")

    return {
        "store": "Target",
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "price": _extract_price(price.get_text() if price else ""),
        "in_stock": "Add to cart" in soup.get_text().lower(),
        "shipping": "Free shipping with RedCard" if "redcard" in soup.get_text().lower() else "",
    }


def _parse_generic(soup: BeautifulSoup, url: str, store_name: str) -> dict:
    """Heuristic fallback for unknown retailers."""
    title = soup.select_one("h1")

    # Try common price selectors
    price = None
    for selector in [
        "[class*='price']", "[id*='price']",
        "[class*='Price']", "[data-price]",
        ".offer-price", ".sale-price", ".current-price"
    ]:
        el = soup.select_one(selector)
        if el and "$" in el.get_text():
            price = el
            break

    return {
        "store": store_name or _domain(url),
        "url": url,
        "title": title.get_text(strip=True) if title else "",
        "price": _extract_price(price.get_text() if price else ""),
        "in_stock": any(kw in soup.get_text().lower() for kw in ["add to cart", "buy now", "in stock"]),
        "shipping": "",
    }


# ---------------------------------------------------------------------------
# Tool 3: compare_and_rank
# ---------------------------------------------------------------------------

def compare_and_rank(product_name: str, results: list) -> dict:
    """
    Sorts and ranks results by price, flags best deal.
    Returns structured comparison ready for display.
    """
    if not results:
        return {"error": "No results to compare."}

    def parse_price(r: dict) -> float:
        raw = r.get("price", "") or ""
        cleaned = re.sub(r"[^\d.]", "", raw)
        try:
            return float(cleaned)
        except ValueError:
            return float("inf")

    valid = [r for r in results if parse_price(r) < float("inf")]
    invalid = [r for r in results if parse_price(r) == float("inf")]

    valid.sort(key=parse_price)

    ranked = []
    for i, r in enumerate(valid):
        price_val = parse_price(r)
        highest = parse_price(valid[-1]) if valid else price_val
        savings = highest - price_val if i > 0 else 0

        ranked.append({
            "rank": i + 1,
            "store": r.get("store", ""),
            "price": r.get("price", ""),
            "price_value": price_val,
            "original_price": r.get("original_price", ""),
            "rating": r.get("rating", ""),
            "shipping": r.get("shipping", ""),
            "in_stock": r.get("in_stock", True),
            "url": r.get("url", ""),
            "notes": r.get("notes", ""),
            "savings_vs_most_expensive": f"${savings:.2f}" if savings > 0 else None,
            "is_best_deal": i == 0,
        })

    # Add unpriced results at the end
    for r in invalid:
        ranked.append({
            "rank": None,
            "store": r.get("store", ""),
            "price": r.get("price", "Price unavailable"),
            "url": r.get("url", ""),
            "in_stock": r.get("in_stock", False),
            "is_best_deal": False,
        })

    best = ranked[0] if ranked else {}
    price_range = ""
    if len(valid) >= 2:
        low = parse_price(valid[0])
        high = parse_price(valid[-1])
        price_range = f"${low:.2f} – ${high:.2f}"

    return {
        "product_name": product_name,
        "best_deal": best,
        "price_range": price_range,
        "stores_checked": len(results),
        "ranked_results": ranked,
    }
