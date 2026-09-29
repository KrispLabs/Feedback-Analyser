"""Lead: run_week() runs the full pipeline in order —
gather -> check -> score -> analyze -> store — and returns results for the
dashboard.

The Gatherer and Scorer are owned by teammates. Until their real modules
land, they're stubbed here with the interfaces agreed in NOTES.md, so
swapping in the real implementations is a one-line change."""

import json
import sys

from analyst import analyze_week
from checker import check_reviews, load_reviews_csv
from memory import HindsightMemory

THEME_KEYWORDS = {
    "login issues": ["login", "log in", "crash"],
    "loading speed": ["load", "loading", "slow"],
    "dark mode": ["dark mode"],
}


def stub_gather_week(week_number: int) -> list[dict]:
    """Placeholder for the Gatherer's real function. Returns cleaned review
    rows: id, source, date, rating, text."""
    return load_reviews_csv(f"data/week_{week_number}_mock.csv")


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
    raw_reviews = stub_gather_week(week_number)
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
