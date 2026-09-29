"""HTTP API for the app's frontend/dashboard to call into the backend
pipeline. Wraps run_week() (gather -> check -> score -> analyze -> store)."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from run_week import run_week

app = FastAPI(title="Feedback Analyser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the real frontend origin before shipping
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/weeks/{week_number}/run")
def run(week_number: int):
    """Runs the full pipeline for one week and returns the result the
    dashboard renders: rejected count, themes, scores, reasoning, next steps."""
    try:
        return run_week(week_number)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No data found for week {week_number}")
