"""
Web UI — FastAPI front-end for the price comparison agent.
"""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

from core.agent import run_agent
from output.renderer import extract_comparison_from_run
from memory.store import append_snapshot, load_history, get_price_trend

app = FastAPI(title="Price Comparison Agent")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/search", response_class=HTMLResponse)
def search(request: Request, product: str = Form(...)):
    run = run_agent(product)
    comparison = extract_comparison_from_run(run)

    trend = None
    if comparison:
        append_snapshot(product, comparison)
        history = load_history(product)
        trend = get_price_trend(product, history)

    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "product": product,
            "final_answer": run.get("final_answer", ""),
            "comparison": comparison,
            "trend": trend,
        },
    )
