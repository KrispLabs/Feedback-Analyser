"""HTTP API for the mobile app / dashboard to call into the backend pipeline.

Two entry points, both running the same stages (gather -> check -> score ->
analyze -> store):

  POST /shops/analyse      one business by name + location (the app's main flow)
  POST /weeks/{n}/run      one ISO week of whatever the Gatherer last collected

Both are slow by design -- they scrape reviews and then make one Groq call per
theme, so 60-120s is normal. See README.md for how a mobile client should
handle that.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from analyse_shop import analyse_shop
from run_week import run_week

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


class ShopRequest(BaseModel):
    name: str = Field(..., examples=["Niloufer Cafe"], description="Business name")
    location: str = Field("", examples=["Hitech City, Hyderabad"])
    months: int = Field(3, ge=0, le=120,
                        description="Only analyse reviews from the last N months; 0 = all time")
    limit: int = Field(200, ge=1, le=1000, description="Max reviews with text to gather")
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
    try:
        return analyse_shop(req.name, req.location, provider=req.provider, limit=req.limit,
                            months=req.months, store=req.store, run_number=req.run_number,
                            verbose=False)
    except LookupError as e:  # nothing found, or nothing survived the Checker
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:  # upstream failed: no API key, provider error, rate limit
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/weeks/{week_number}/run")
def run(week_number: int):
    """Runs the full pipeline for one ISO week of already-gathered data and
    returns the result the dashboard renders: rejected count, themes, scores,
    reasoning, next steps."""
    try:
        return run_week(week_number)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No data found for week {week_number}")
