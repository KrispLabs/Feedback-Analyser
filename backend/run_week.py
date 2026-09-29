"""Lead: run_week() runs the full pipeline in order —
gather -> check -> score -> analyze -> store — and returns results for the
dashboard.

Gather uses the real Gatherer (backend/gatherer/, pulled in from the sarthak
branch): Telco customer feedback + Verizon/AT&T/Xfinity Play Store reviews,
see NOTES.md. Score uses Karthik's real scorer.py (LLM-based theme
discovery), pulled in from the Karthik branch."""

import json
import sys

import pandas as pd

from analyst import analyze_week
from checker import check_reviews
from gatherer.gatherer import DEFAULT_OUT, load as load_gathered
from memory import HindsightMemory
from scorer import extract_themes


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


def run_week(week_number: int) -> dict:
    raw_reviews = gather_week(week_number)
    verified, rejected_count, rejected_by_reason = check_reviews(raw_reviews)
    themes = extract_themes(verified, rejected_count)

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
    import argparse

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Run the full pipeline for one week.")
    ap.add_argument("week", nargs="?", type=int, default=1,
                    help="1-indexed into the ISO weeks the Gatherer produced (default: 1)")
    ap.add_argument("--weeks", action="store_true", help="list available weeks and exit")
    args = ap.parse_args()

    if args.weeks:
        print("\n".join(f"{i}: {w}" for i, w in enumerate(_available_weeks(), 1)))
        sys.exit()
    print(json.dumps(run_week(args.week), indent=2))
