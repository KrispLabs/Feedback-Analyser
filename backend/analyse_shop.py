"""Interactive end-to-end run for one shop.

Ask for a business name and location, gather its reviews off the web, filter
out the junk, group what's left into themes, score each theme -5..+5 with
reasoning, and store the result so the next run can spot trends.

  python analyse_shop.py                                  # prompts for both
  python analyse_shop.py "Niloufer Cafe" "Hitech City"
  python analyse_shop.py "Niloufer Cafe" "Hitech City" --limit 200 --months 6

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
from config import get_key
from errors import ConfigError, NothingToAnalyse, PipelineError, UpstreamError
from gatherer.gatherer import DEFAULT_OUT, gather, write
from gatherer.sources import REGISTRY
from gatherer.sources.shop import MAX_PAGES
import market as mkt
from memory import HindsightMemory
from scorer import extract_themes

WIDTH = 78
# Analyse the newest N reviews that have text, rather than a time window: a
# quiet shop has too few reviews in 3 months to find themes, and a busy one has
# thousands. See MAX_PAGES in shop.py for what this costs in SerpApi searches.
DEFAULT_LIMIT = 400


def bizname_for(name: str, location: str) -> str:
    # name + location, so two branches of one chain keep separate histories
    return f"{name}, {location}" if location else name


def _quiet(*args) -> None:
    pass


def wrap(text: str, indent: str = "      ") -> str:
    return textwrap.fill(str(text), width=WIDTH, initial_indent=indent, subsequent_indent=indent)


def analyse_shop(name: str, location: str, provider: str = "serpapi", limit: int = DEFAULT_LIMIT,
                 store: bool = True, run_number: int = 1, max_pages: int = MAX_PAGES,
                 months: int = 0, verbose: bool = True, compare: bool = False,
                 competitors: list[str] | None = None,
                 competitor_count: int = mkt.DEFAULT_COMPETITORS) -> dict:
    """compare: also scan the local market -- the competitors named in
    `competitors`, or else the `competitor_count` busiest places of the same
    kind nearby -- and let the Analyst score each theme against them.
    Naming competitors implies compare."""
    """Raises NothingToAnalyse, UpstreamError or ConfigError (errors.py) for
    the failures a caller should expect. Anything short of fatal -- a provider
    dying partway through, the CSV not being writable, Hindsight being down --
    becomes an entry in result["warnings"] instead of losing the whole run."""
    # Print only in CLI mode; api.py passes verbose=False. A local, not a
    # module global: the API serves requests on a thread pool, so a global
    # flag set by one request would silence or un-silence another.
    say = print if verbose else _quiet
    warnings: list[str] = []

    def warn(message: str) -> None:
        warnings.append(message)
        say(wrap(f"⚠ {message}"))

    def rule(title: str = "") -> None:
        say(f"\n{'─' * WIDTH}" if not title else f"\n── {title} " + "─" * max(0, WIDTH - len(title) - 4))

    name, location = (name or "").strip(), (location or "").strip()
    if not name:
        raise NothingToAnalyse("A business name is required.")
    say(f"\n{'=' * WIDTH}\n  {name} — {location}\n{'=' * WIDTH}")

    # 0. PREFLIGHT ----------------------------------------------------------
    # Check keys before gathering: a missing Groq key used to surface only at
    # step 3, after up to max_pages billable SerpApi searches were spent.
    since = (date.today() - timedelta(days=round(months * 30.44))).isoformat() if months else None
    source = REGISTRY["shop"](name=name, location=location, provider=provider, limit=limit,
                              max_pages=max_pages, since=since)
    if not get_key("GROQ_API_KEY"):
        raise ConfigError("GROQ_API_KEY is not set -- see .env.example, or add it to keys.csv.")
    try:
        source._key()
    except RuntimeError as e:
        raise ConfigError(str(e)) from e

    # 1. GATHER -------------------------------------------------------------
    rule("1/5  Gathering reviews from the web")
    say(f"      source   : {source!r}")
    plural = "month" if months == 1 else "months"
    say(f"      target   : newest {limit} reviews with text"
        + (f", from the last {months} {plural} (since {since})" if since else ""))
    errors: list = []
    reviews = gather([source], log=lambda *a: None, errors=errors)
    failure = f"{errors[0][1]}" if errors else ""
    if reviews.empty:
        if errors:  # the provider failed -- not the same as "no reviews exist"
            raise UpstreamError(f"Couldn't fetch reviews for {name!r} via {provider}: {failure}")
        raise NothingToAnalyse(
            f"No reviews found for {name!r} in {location!r}"
            + (f" since {since}. Widen the window (months=0 for all time)." if since else ".")
            + " Otherwise try a fuller address, or pin the branch with place_id.")
    if errors:
        warn(f"Review fetching stopped early after {len(reviews)} reviews ({failure}); "
             f"analysing what was fetched.")

    dated = reviews[reviews["date"] != ""]["date"]
    rated = pd.to_numeric(reviews["rating"], errors="coerce").dropna()
    say(f"      gathered : {len(reviews)} reviews"
          + (f", {dated.min()} .. {dated.max()}" if len(dated) else ", no dates"))
    if len(rated):
        stars = "".join(f"  {s}★ {(rated == s).sum()}" for s in (5, 4, 3, 2, 1))
        say(f"      ratings  : avg {rated.mean():.2f}{stars}")
    try:  # the CSV is a record for run_week(), not needed for this analysis
        full = write(reviews, DEFAULT_OUT, append=True)
        say(f"      saved    : {DEFAULT_OUT}  ({len(full)} rows in the database)")
    except Exception as e:
        warn(f"Couldn't save reviews to {DEFAULT_OUT} ({type(e).__name__}: {e}); "
             f"the analysis continues without them.")
    if source.pages_fetched:
        capped = (f" (page cap hit — raise --max-pages to reach {limit})"
                  if source.pages_fetched >= max_pages and len(reviews) < limit else "")
        say(f"      cost     : {source.pages_fetched} billable SerpApi searches{capped}")

    # 2. CHECK --------------------------------------------------------------
    rule("2/5  Checking (filtering spam, duplicates, gibberish)")
    verified, rejected_count, by_reason = check_reviews(reviews.to_dict("records"))
    say(f"      verified : {len(verified)} of {len(reviews)}")
    say(f"      rejected : {rejected_count}")
    for reason, n in sorted(by_reason.items(), key=lambda kv: -kv[1]):
        say(f"                 {reason:<18} {n}")
    if not verified:
        raise NothingToAnalyse(f"All {len(reviews)} reviews for {name!r} were rejected by the "
                               f"Checker ({dict(by_reason)}) — nothing left to analyse.")

    # 3. SCORE (theme discovery) --------------------------------------------
    rule("3/5  Finding themes")
    themes = extract_themes(verified, rejected_count)
    if not themes:
        # empty is ambiguous: genuinely no pattern, or a silently failed LLM call
        raise UpstreamError(f"The Scorer found no themes in {len(verified)} verified reviews. "
                            f"Usually means the Groq call failed or hit a rate limit.")
    say(f"      found    : {len(themes)} themes across {len(verified)} verified reviews")
    for t in themes:
        say(f"                 {t['name'][:46]:<46} {t['count']:>4} mentions")

    # 3b. SIMILAR MARKET ---------------------------------------------------
    market = None
    if compare or competitors:
        rule("3b/5 Reading nearby competitors' reviews")
        found, discovered = mkt.find_competitors(source, competitors or [], location,
                                                 n=max(1, min(competitor_count, mkt.MAX_COMPETITORS)),
                                                 warn=warn)
        say(f"      found    : {', '.join(c['name'] for c in found) or 'none'}"
            + (" (nearby, same category)" if discovered and found else ""))
        groups, pages = mkt.gather_competitors(found, location, provider, since, warn=warn)
        if pages:
            say(f"      cost     : {pages} more billable SerpApi searches")
        meta = {c["name"]: c for c in found}
        summary = mkt.summarise(bizname_for(name, location), groups, meta, warn=warn)
        for c in summary:
            say(f"      {c['name']}: {c['reviews_used']} reviews · "
                f"+ {'; '.join(p['point'] for p in c['strengths']) or '-'} · "
                f"- {'; '.join(p['point'] for p in c['weaknesses']) or '-'}")
        market = {"discovered": discovered, "competitors": summary}

    # 4 + 5. ANALYSE AND STORE ----------------------------------------------
    rule("4/5  Scoring each theme (-5..+5) with reasoning")
    business = bizname_for(name, location)
    with HindsightMemory(business) as memory:
        if memory.available:
            say(f"      memory   : Hindsight bank {memory.bank_id!r}, scoped to {memory.tag!r}\n")
        period = (f"{dated.min()} to {dated.max()}" if len(dated) else
                  (f"the last {months} {plural}" if months else "all time"))
        analyzed = analyze_week(themes, memory, business=business, period=period,
                                market=mkt.context_for_analyst(market["competitors"]) if market else "")
        memory_failed_early = memory.error is not None  # after: recall can fail partway
        if memory_failed_early:
            warn(f"{memory.error}; scored without past-run trends, and this run isn't stored.")

        for t in sorted(analyzed, key=lambda t: t["score"]):
            # degraded = Groq unavailable or an unusable reply: its 0 is a
            # placeholder, so say so loudly instead of passing it off as neutral
            flag = "  ⚠ NOT A REAL SCORE" if t["degraded"] else ""
            say(f"  {t['score']:+d}   {t['name']}   ({t['count']} mentions){flag}")
            say(wrap(f"why   {t['reasoning']}"))
            say(wrap(f"do    {t['next_step']}") + "\n")

        result = {"week": run_number, "business": name, "location": location, "period": period,
                  "reviews_gathered": len(reviews), "reviews_verified": len(verified),
                  "rejected_count": rejected_count, "rejected_by_reason": by_reason,
                  "themes": analyzed, "market": market, "warnings": warnings}

        rule("5/5  Storing for next time")
        # keyed by day as well as run number: re-running today replaces
        # today's memory, but API callers that leave run_number at its default
        # of 1 still build up history across days instead of overwriting it
        result["stored"] = False  # true only once Hindsight has actually kept it
        if not store:
            say("      skipped (--no-store)")
        elif memory.store_week(run_number, result,
                               run_key=f"run:{run_number}:{date.today().isoformat()}"):
            result["stored"] = True
            say(f"      stored   : run {run_number} -> bank {memory.bank_id!r}")
            say("      next run recalls this to spot trends ('worse than last time')")
        elif memory.error and not memory_failed_early:  # recall worked, the store failed
            warn(f"{memory.error}; this run isn't stored for trend recall.")
        else:
            say("      skipped: no theme was really scored, nothing worth remembering")

    # SUMMARY ---------------------------------------------------------------
    degraded = [t for t in analyzed if t["degraded"]]
    real = [t for t in analyzed if t not in degraded]
    rule("SUMMARY")
    if real:
        worst, best = min(real, key=lambda t: t["score"]), max(real, key=lambda t: t["score"])
        say(f"      Fix first  : {worst['name']} ({worst['score']:+d})")
        say(wrap(worst["next_step"], "                   "))
        say(f"      Protect    : {best['name']} ({best['score']:+d})")
        say(wrap(best["next_step"], "                   "))
    if degraded:
        warnings.append(f"{len(degraded)} of {len(analyzed)} themes could not be scored "
                        f"(Groq unavailable, rate limited, or an unusable reply); see themes[].degraded.")
        say(f"\n      ⚠ {len(degraded)} of {len(analyzed)} themes could NOT be scored — Groq was "
              f"unavailable, rate\n        limited, or replied unusably. Those show +0 but are not real results.")
    say("")
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="End-to-end feedback analysis for one shop.")
    ap.add_argument("name", nargs="?", help='business name, e.g. "Niloufer Cafe"')
    ap.add_argument("location", nargs="?", help='e.g. "Hitech City, Hyderabad"')
    ap.add_argument("--provider", default="serpapi", choices=["places", "serpapi"],
                    help="serpapi = hundreds of reviews; places = official Google API, max 5")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help=f"analyse the newest N reviews with text (default: {DEFAULT_LIMIT})")
    ap.add_argument("--run", type=int, default=1, dest="run_number",
                    help="run number, stored in Hindsight so later runs compare (default: 1)")
    ap.add_argument("--months", type=int, default=0,
                    help="also stop at reviews older than N months; 0 = no age limit (default: 0)")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES,
                    help=f"cap on billable SerpApi searches (default: {MAX_PAGES})")
    ap.add_argument("--no-store", action="store_true", help="don't write to Hindsight")
    ap.add_argument("--compare", action="store_true",
                    help="also analyse the busiest similar places nearby, as the local market")
    ap.add_argument("--competitor", action="append", default=[], dest="competitors",
                    help="a competitor to compare with (repeatable); implies --compare")
    args = ap.parse_args()

    try:
        name = args.name or input("Business name : ").strip()
        location = args.location if args.location is not None else input("Location      : ").strip()
        analyse_shop(name, location, provider=args.provider, limit=args.limit,
                     store=not args.no_store, run_number=args.run_number,
                     max_pages=args.max_pages, months=args.months,
                     compare=args.compare, competitors=args.competitors)
    except PipelineError as e:
        sys.exit(f"\n  {e}\n")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\n  Cancelled.\n")


if __name__ == "__main__":
    main()
