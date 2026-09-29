"""Lead: run_week() runs the full pipeline in order —
gather -> check -> score -> analyze -> store — and returns results for the
dashboard.

Gather uses the real Gatherer (backend/gatherer/, pulled in from the sarthak
branch): Telco customer feedback + Verizon/AT&T/Xfinity Play Store reviews,
see NOTES.md. Score uses Karthik's real scorer.py (LLM-based theme
discovery), pulled in from the Karthik branch.

One run analyses ONE business's own reviews. The cleaned CSV holds several
businesses (Telco, its competitors under origin=market, and every shop
analyse_shop.py has appended), and loading a whole week used to score all of
them as one: Verizon's app-update complaints came out as Telco's -5."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analyst import analyze_week
from checker import check_reviews
from gatherer.gatherer import DEFAULT_OUT, load as load_gathered
from gatherer.schema import OWN
from memory import HindsightMemory
from scorer import extract_themes

GATHERER_CONFIG = Path(__file__).resolve().parent / "gatherer_config.json"


def default_business() -> str:
    """The business gatherer_config.json gathers for (currently "Telco")."""
    return json.loads(GATHERER_CONFIG.read_text())["business"]


def _own_reviews(business: str) -> pd.DataFrame:
    df = load_gathered(DEFAULT_OUT, origin=OWN)
    df = df[(df["business"] == business) & (df["week"] != "")]
    if df.empty:
        known = sorted(load_gathered(DEFAULT_OUT, origin=OWN)["business"].unique())
        raise FileNotFoundError(f"no dated reviews for business {business!r}; "
                                f"gathered businesses: {known}")
    return df


def _available_weeks(business: str) -> list[str]:
    """Chronological ISO weeks present in this business's own reviews."""
    return sorted(_own_reviews(business)["week"].unique())


def gather_week(week_number: int, business: str) -> list[dict]:
    """week_number is 1-indexed into the chronological ISO weeks this
    business has reviews for (e.g. week 1 = its earliest week gathered)."""
    df = _own_reviews(business)
    weeks = sorted(df["week"].unique())
    if not (1 <= week_number <= len(weeks)):
        raise FileNotFoundError(f"week {week_number} out of range for {business!r} "
                                f"(1..{len(weeks)} available)")
    return df[df["week"] == weeks[week_number - 1]].to_dict("records")


def run_week(week_number: int, business: str | None = None) -> dict:
    business = business or default_business()
    raw_reviews = gather_week(week_number, business)
    dates = sorted(r["date"] for r in raw_reviews)
    period = f"{dates[0]} to {dates[-1]}"

    verified, rejected_count, rejected_by_reason = check_reviews(raw_reviews)
    if not verified:
        raise LookupError(f"all {len(raw_reviews)} reviews for {business!r} week {week_number} "
                          f"were rejected by the Checker ({rejected_by_reason})")
    themes = extract_themes(verified, rejected_count)
    if not themes:
        # empty is ambiguous (see analyse_shop.py) -- never store it as a real week
        raise RuntimeError(f"the Scorer found no themes in {len(verified)} verified reviews; "
                           f"usually means the Groq call failed or hit a rate limit")

    with HindsightMemory(business) as memory:
        analyzed_themes = analyze_week(themes, memory, business=business, period=period,
                                       before_week=week_number)
        week_result = {
            "week": week_number,
            "business": business,
            "period": period,
            "rejected_count": rejected_count,
            "rejected_by_reason": rejected_by_reason,
            "themes": analyzed_themes,
        }
        memory.store_week(week_number, week_result,
                          timestamp=datetime.fromisoformat(dates[0]).replace(tzinfo=timezone.utc))

    return week_result


if __name__ == "__main__":
    import argparse

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Run the full pipeline for one week.")
    ap.add_argument("week", nargs="?", type=int, default=1,
                    help="1-indexed into the ISO weeks the Gatherer produced (default: 1)")
    ap.add_argument("--business", help="whose own reviews to analyse "
                                       "(default: the business in gatherer_config.json)")
    ap.add_argument("--weeks", action="store_true", help="list available weeks and exit")
    args = ap.parse_args()
    business = args.business or default_business()

    if args.weeks:
        print("\n".join(f"{i}: {w}" for i, w in enumerate(_available_weeks(business), 1)))
        sys.exit()
    print(json.dumps(run_week(args.week, business), indent=2))
