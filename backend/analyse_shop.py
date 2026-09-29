"""Interactive end-to-end run for one shop.

Ask for a business name and location, gather its reviews off the web, filter
out the junk, group what's left into themes, score each theme -5..+5 with
reasoning, and store the result so the next run can spot trends.

  python analyse_shop.py                                  # prompts for both
  python analyse_shop.py "Niloufer Cafe" "Hitech City"
  python analyse_shop.py "Niloufer Cafe" "Hitech City" --provider serpapi --limit 300

Same pipeline as run_week() (gather -> check -> score -> analyze -> store), but
over one shop's whole review history rather than one ISO week: a shop you've
just looked up has no prior weeks to slice.
"""

import argparse
import sys
import textwrap
from datetime import date, timedelta

import pandas as pd

from analyst import analyze_week
from checker import check_reviews
from gatherer.gatherer import DEFAULT_OUT, gather, write
from gatherer.sources import REGISTRY
from gatherer.sources.shop import MAX_PAGES
from memory import HindsightMemory
from scorer import extract_themes

WIDTH = 78
# analyst.py's fallback reasoning, emitted when Groq is unreachable or rate
# limited. It arrives as a normal-looking score of 0, so the pipeline can't
# tell you it failed -- catch it here and say so loudly instead.
FALLBACK_MARKER = "LLM unavailable"


_verbose = True


def say(*args) -> None:
    """Print only in CLI mode. api.py calls the same function with verbose=False."""
    if _verbose:
        print(*args)


def rule(title: str = "") -> None:
    say(f"\n{'─' * WIDTH}" if not title else f"\n── {title} " + "─" * max(0, WIDTH - len(title) - 4))


def wrap(text: str, indent: str = "      ") -> str:
    return textwrap.fill(str(text), width=WIDTH, initial_indent=indent, subsequent_indent=indent)


def analyse_shop(name: str, location: str, provider: str = "serpapi", limit: int = 200,
                 store: bool = True, run_number: int = 1, max_pages: int = MAX_PAGES,
                 months: int = 3, verbose: bool = True) -> dict:
    global _verbose
    _verbose = verbose
    say(f"\n{'=' * WIDTH}\n  {name} — {location}\n{'=' * WIDTH}")

    # 1. GATHER -------------------------------------------------------------
    rule("1/5  Gathering reviews from the web")
    since = (date.today() - timedelta(days=round(months * 30.44))).isoformat() if months else None
    source = REGISTRY["shop"](name=name, location=location, provider=provider, limit=limit,
                              max_pages=max_pages, since=since)
    say(f"      source   : {source!r}")
    plural = "month" if months == 1 else "months"
    say(f"      window   : " + (f"last {months} {plural} (since {since})" if since else "all time"))
    reviews = gather([source], log=lambda *a: None)
    if reviews.empty:
        raise LookupError(
            f"No reviews found for {name!r} in {location!r}"
            + (f" since {since}. Widen the window (months=0 for all time)." if since else ".")
            + " Otherwise try a fuller address, or pin the branch with place_id.")

    full = write(reviews, DEFAULT_OUT, append=True)
    dated = reviews[reviews["date"] != ""]["date"]
    rated = pd.to_numeric(reviews["rating"], errors="coerce").dropna()
    say(f"      gathered : {len(reviews)} reviews"
          + (f", {dated.min()} .. {dated.max()}" if len(dated) else ", no dates"))
    if len(rated):
        stars = "".join(f"  {s}★ {(rated == s).sum()}" for s in (5, 4, 3, 2, 1))
        say(f"      ratings  : avg {rated.mean():.2f}{stars}")
    say(f"      saved    : {DEFAULT_OUT}  ({len(full)} rows in the database)")
    if source.pages_fetched:
        capped = " (page cap hit — raise --max-pages for more)" if source.pages_fetched >= max_pages else ""
        say(f"      cost     : {source.pages_fetched} billable SerpApi searches{capped}")

    # 2. CHECK --------------------------------------------------------------
    rule("2/5  Checking (filtering spam, duplicates, gibberish)")
    verified, rejected_count, by_reason = check_reviews(reviews.to_dict("records"))
    say(f"      verified : {len(verified)} of {len(reviews)}")
    say(f"      rejected : {rejected_count}")
    for reason, n in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        say(f"                 {reason:<18} {n}")
    if not verified:
        raise LookupError(f"All {len(reviews)} reviews for {name!r} were rejected by the "
                          f"Checker ({dict(by_reason)}) — nothing left to analyse.")

    # 3. SCORE (theme discovery) --------------------------------------------
    rule("3/5  Finding themes")
    themes = extract_themes(verified, rejected_count)
    if not themes:
        # empty is ambiguous: genuinely no pattern, or a silently failed LLM call
        raise RuntimeError(f"The Scorer found no themes in {len(verified)} verified reviews. "
                           f"Usually means the Groq call failed or hit a rate limit.")
    say(f"      found    : {len(themes)} themes across {len(verified)} verified reviews")
    for t in themes:
        say(f"                 {t['name'][:46]:<46} {t['count']:>4} mentions")

    # 4 + 5. ANALYSE AND STORE ----------------------------------------------
    rule("4/5  Scoring each theme (-5..+5) with reasoning")
    with HindsightMemory() as memory:
        say(f"      memory   : Hindsight bank {memory.bank_id!r}\n")
        period = (f"{dated.min()} to {dated.max()}" if len(dated) else
                  (f"the last {months} {plural}" if months else "all time"))
        analyzed = analyze_week(themes, memory, business=f"{name}, {location}", period=period)

        for t in sorted(analyzed, key=lambda t: t["score"]):
            flag = "  ⚠ NOT A REAL SCORE" if FALLBACK_MARKER in t["reasoning"] else ""
            say(f"  {t['score']:+d}   {t['name']}   ({t['count']} mentions){flag}")
            say(wrap(f"why   {t['reasoning']}"))
            say(wrap(f"do    {t['next_step']}") + "\n")

        result = {"week": run_number, "business": name, "location": location, "period": period,
                  "rejected_count": rejected_count, "rejected_by_reason": by_reason,
                  "themes": analyzed}

        rule("5/5  Storing for next time")
        if store:
            memory.store_week(run_number, result)
            say(f"      stored   : run {run_number} -> bank {memory.bank_id!r}")
            say("      next run recalls this to spot trends ('worse than last time')")
        else:
            say("      skipped (--no-store)")

    # SUMMARY ---------------------------------------------------------------
    degraded = [t for t in analyzed if FALLBACK_MARKER in t["reasoning"]]
    real = [t for t in analyzed if t not in degraded]
    rule("SUMMARY")
    if real:
        worst, best = min(real, key=lambda t: t["score"]), max(real, key=lambda t: t["score"])
        say(f"      Fix first  : {worst['name']} ({worst['score']:+d})")
        say(wrap(worst["next_step"], "                   "))
        say(f"      Protect    : {best['name']} ({best['score']:+d})")
        say(wrap(best["next_step"], "                   "))
    if degraded:
        say(f"\n      ⚠ {len(degraded)} of {len(analyzed)} themes could NOT be scored — Groq was "
              f"unavailable or\n        rate limited. Those show +0 but are not real results.")
    say("")
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="End-to-end feedback analysis for one shop.")
    ap.add_argument("name", nargs="?", help='business name, e.g. "Niloufer Cafe"')
    ap.add_argument("location", nargs="?", help='e.g. "Hitech City, Hyderabad"')
    ap.add_argument("--provider", default="serpapi", choices=["places", "serpapi"],
                    help="serpapi = hundreds of reviews; places = official Google API, max 5")
    ap.add_argument("--limit", type=int, default=200, help="max reviews to gather (default: 200)")
    ap.add_argument("--run", type=int, default=1, dest="run_number",
                    help="run number, stored in Hindsight so later runs compare (default: 1)")
    ap.add_argument("--months", type=int, default=3,
                    help="only analyse reviews from the last N months; 0 = all time (default: 3)")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES,
                    help=f"cap on billable SerpApi searches (default: {MAX_PAGES})")
    ap.add_argument("--no-store", action="store_true", help="don't write to Hindsight")
    args = ap.parse_args()

    name = args.name or input("Business name : ").strip()
    location = args.location if args.location is not None else input("Location      : ").strip()
    if not name:
        sys.exit("A business name is required.")

    try:
        analyse_shop(name, location, provider=args.provider, limit=args.limit,
                     store=not args.no_store, run_number=args.run_number,
                     max_pages=args.max_pages, months=args.months)
    except (LookupError, RuntimeError) as e:
        sys.exit(f"\n  {e}\n")


if __name__ == "__main__":
    main()
