"""
Memory store — persists price-comparison snapshots per product so repeat
searches can show how prices have changed over time.
"""

import json
import re
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("memory/data")


def _slug(product_name: str) -> str:
    return re.sub(r"[^\w\s-]", "", product_name).strip().replace(" ", "_")[:40]


def _history_path(product_name: str) -> Path:
    return MEMORY_DIR / f"{_slug(product_name)}.json"


def load_history(product_name: str) -> list:
    """Returns the list of past snapshots for a product, or [] if none exist."""
    path = _history_path(product_name)
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)


def append_snapshot(product_name: str, comparison: dict) -> dict:
    """
    Records a new snapshot of the best deal for a product and writes it to disk.
    Returns the snapshot that was appended.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    best = comparison.get("best_deal", {}) or {}
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "best_deal": {
            "store": best.get("store", ""),
            "price": best.get("price", ""),
            "price_value": best.get("price_value"),
            "url": best.get("url", ""),
        },
        "price_range": comparison.get("price_range", ""),
        "stores_checked": comparison.get("stores_checked", 0),
    }

    history = load_history(product_name)
    history.append(snapshot)

    with open(_history_path(product_name), "w") as f:
        json.dump(history, f, indent=2, default=str)

    return snapshot


def get_price_trend(product_name: str, history: list) -> dict | None:
    """
    Compares the most recent snapshot to the one before it.
    Returns None if there isn't enough history to compare.
    """
    if len(history) < 2:
        return None

    previous, current = history[-2], history[-1]
    prev_price = previous.get("best_deal", {}).get("price_value")
    curr_price = current.get("best_deal", {}).get("price_value")

    if prev_price is None or curr_price is None:
        return None

    change = curr_price - prev_price
    change_pct = (change / prev_price * 100) if prev_price else 0

    if change < 0:
        direction = "down"
    elif change > 0:
        direction = "up"
    else:
        direction = "same"

    return {
        "previous_price": prev_price,
        "previous_date": previous.get("timestamp", ""),
        "previous_store": previous.get("best_deal", {}).get("store", ""),
        "current_price": curr_price,
        "change": change,
        "change_pct": change_pct,
        "direction": direction,
    }
