"""HTTP API for the mobile app / dashboard to call into the backend pipeline.

Two entry points, both running the same stages (gather -> check -> score ->
analyze -> store):

  POST /shops/analyse      one business by name + location (the app's main flow)
  POST /weeks/{n}/run      one ISO week of whatever the Gatherer last collected

Both are slow by design -- they scrape reviews and then make one Groq call per
theme, so 60-120s is normal. See README.md for how a mobile client should
handle that.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from analyse_shop import DEFAULT_LIMIT, analyse_shop
from errors import PipelineError
from run_week import run_week

log = logging.getLogger("feedback.api")

app = FastAPI(
    title="Feedback Analyser API",
    description="Turns public reviews for a business into scored, explained themes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real frontend origin before shipping
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PipelineError)
def pipeline_error(request: Request, exc: PipelineError):
    """Expected failures, one status each (see errors.py): 404 nothing to
    analyse, 502 an upstream service failed (retriable), 503 server config."""
    return JSONResponse(status_code=exc.status,
                        content={"detail": str(exc), "error": type(exc).__name__})


@app.exception_handler(Exception)
def unexpected_error(request: Request, exc: Exception):
    """A bug, not an expected failure. Answer in the same JSON shape as every
    other error instead of a plain-text 500; the traceback still goes to the
    server log."""
    # exc_info explicitly: handlers run outside the except block, so
    # log.exception() would log "NoneType: None" instead of the traceback
    log.error("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={
        "detail": f"Internal error ({type(exc).__name__}). This is a bug; the server log has details.",
        "error": "InternalError"})


class ShopRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, examples=["Niloufer Cafe"], description="Business name")
    location: str = Field("", examples=["Hitech City, Hyderabad"])
    limit: int = Field(DEFAULT_LIMIT, ge=1, le=1000,
                       description="Analyse the newest N reviews that have text")
    months: int = Field(0, ge=0, le=120,
                        description="Also skip reviews older than N months; 0 = no age limit")
    provider: str = Field("serpapi", pattern="^(serpapi|places)$",
                          description="serpapi = hundreds of reviews; places = Google's API, max 5")
    store: bool = Field(True, description="Write the result to Hindsight for trend recall")
    run_number: int = Field(1, ge=1, description="Numbers this run so later runs compare against it")


@app.get("/health")
def health():
    """Liveness check. Cheap, hits no external service."""
    return {"status": "ok"}


@app.post("/shops/analyse")
def analyse(req: ShopRequest):
    """Analyse one business by name and location — the app's main flow.

    Scrapes its public reviews, filters junk, groups the rest into themes, and
    scores each -5..+5 with reasoning and a recommended next step.
    """
    return analyse_shop(req.name, req.location, provider=req.provider, limit=req.limit,
                        months=req.months, store=req.store, run_number=req.run_number,
                        verbose=False)


@app.post("/weeks/{week_number}/run")
def run(week_number: int, business: str | None = None):
    """Runs the full pipeline for one ISO week of one business's already-gathered
    reviews and returns the result the dashboard renders: rejected count, themes,
    scores, reasoning, next steps. `business` defaults to the one in
    gatherer_config.json; competitor (market) reviews are never mixed in."""
    return run_week(week_number, business)
