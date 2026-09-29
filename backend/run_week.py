"""Lead: run_week() runs the full pipeline in order —
gather -> check -> score -> analyze -> store — and returns results for the
dashboard.

Gather now uses the real Gatherer (backend/gatherer/, pulled in from the
sarthak branch): Telco customer feedback + Verizon/AT&T/Xfinity Play Store
reviews, see NOTES.md. Score is still a stub for the Scorer's real
theme-grouping/llm.py."""

import json
import sys

import pandas as pd

from analyst import analyze_week
from checker import check_reviews
from gatherer.gatherer import DEFAULT_OUT, load as load_gathered
from memory import HindsightMemory

THEME_KEYWORDS = {
    "billing & pricing": ["monthly charge", "expensive", "price", "bill", "cost"],
    "internet reliability": ["downtime", "reliable", "outage", "slow", "speed"],
    "customer service": ["customer service", "support", "technician", "help desk", "representative"],
    "app login issues": ["sign in", "log in", "login", "password", "blank"],
}


def _available_weeks() -> list[str]:
    """Chronological ISO weeks present in the Gatherer's cleaned output."""
    df = pd.read_csv(DEFAULT_OUT, usecols=["week"], dtype=str)
    return sorted(df["week"].dropna().unique())


def gather_week(week_number: int) -> list[dict]:
    """week_number is 1-indexed into the chronological ISO weeks the real
    Gatherer produced (e.g. week 1 = the earliest week gathered)."""
    weeks = _available_weeks()
    if not (1 <= week_number <= len(weeks)):
        raise FileNotFoundError(f"week {week_number} out of range (1..{len(weeks)} available)")
    df = load_gathered(DEFAULT_OUT, week=weeks[week_number - 1])
    return df.to_dict("records")


def stub_score_themes(verified_reviews: list[dict]) -> list[dict]:
    """Placeholder for the Scorer's real theme-grouping/llm.py. Returns
    [{"name", "count", "samples"}, ...] via naive keyword matching, just so
    the pipeline is exercisable end-to-end before the real Scorer lands."""
    themes = []
    for name, keywords in THEME_KEYWORDS.items():
        matched = [r for r in verified_reviews if any(kw in r["text"].lower() for kw in keywords)]
        if matched:
            themes.append({"name": name, "count": len(matched), "samples": [r["text"] for r in matched[:3]]})
    return themes


def run_week(week_number: int) -> dict:
    raw_reviews = gather_week(week_number)
    verified, rejected_count, rejected_by_reason = check_reviews(raw_reviews)
    themes = stub_score_themes(verified)

    with HindsightMemory() as memory:
        analyzed_themes = analyze_week(themes, memory)
        week_result = {
            "week": week_number,
            "rejected_count": rejected_count,
            "rejected_by_reason": rejected_by_reason,
            "themes": analyzed_themes,
        }
        memory.store_week(week_number, week_result)

    return week_result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(run_week(1), indent=2))
