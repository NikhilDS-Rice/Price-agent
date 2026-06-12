#!/usr/bin/env python3
"""
Price Comparison Agent — Web UI entrypoint

Usage:
  python web_main.py
  Then open http://127.0.0.1:8000 in your browser.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
