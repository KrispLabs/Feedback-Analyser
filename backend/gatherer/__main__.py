"""CLI. Run from backend/:

  python -m gatherer shop "Chai Point" "Banjara Hills, Hyderabad"
  python -m gatherer shop "Chai Point" "Hyderabad" --provider serpapi --limit 300
  python -m gatherer --config gatherer_config.json
  python -m gatherer --config gatherer_config.json --since 2026-01-01 --min-chars 3
  python -m gatherer inspect ../data/raw/*.csv

Note: the shared flags (--out, --since, --until, --min-chars) belong to the top
level, so they go before the subcommand.
"""

import argparse
from pathlib import Path

from .gatherer import DEFAULT_OUT, run, run_shop
from .inspect_csv import inspect
from .schema import OWN, MARKET
from .sources.shop import KEY_ENV, MAX_PAGES, SERPAPI_SORT


def main():
    ap = argparse.ArgumentParser(prog="gatherer")
    sub = ap.add_subparsers(dest="cmd")

    ins = sub.add_parser("inspect", help="profile raw CSVs and suggest a column mapping")
    ins.add_argument("paths", nargs="+")
    ins.add_argument("--rows", type=int, default=3)

    sh = sub.add_parser("shop", help="one shop by name + location -> appended to the CSV database")
    sh.add_argument("name", help='shop name, e.g. "Chai Point"')
    sh.add_argument("location", nargs="?", default="", help='e.g. "Banjara Hills, Hyderabad"')
    sh.add_argument("--provider", default="places", choices=sorted(KEY_ENV),
                    help="places = official Google API but max 5 reviews; "
                         "serpapi = hundreds per shop (default: places)")
    sh.add_argument("--limit", type=int, default=100, help="max reviews (default: 100)")
    sh.add_argument("--origin", default=OWN, choices=[OWN, MARKET],
                    help=f"{OWN} = your business, {MARKET} = a competitor (default: {OWN})")
    sh.add_argument("--sort", default="newest", choices=sorted(SERPAPI_SORT))
    sh.add_argument("--place-id", help="skip the name lookup when it keeps picking the wrong branch")
    sh.add_argument("--max-pages", type=int, default=MAX_PAGES,
                    help=f"cap on billable SerpApi searches (default: {MAX_PAGES})")
    sh.add_argument("--replace", action="store_true",
                    help="overwrite the database instead of adding to it")

    ap.add_argument("--config", default="gatherer_config.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--since", help="keep reviews on/after YYYY-MM-DD")
    ap.add_argument("--until", help="keep reviews on/before YYYY-MM-DD")
    ap.add_argument("--min-chars", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "inspect":
        for p in args.paths:
            inspect(p, sample_rows=args.rows)
    elif args.cmd == "shop":
        run_shop(args.name, args.location, out=args.out, append=not args.replace,
                 min_chars=args.min_chars, since=args.since, until=args.until,
                 provider=args.provider, limit=args.limit, origin=args.origin,
                 sort=args.sort, place_id=args.place_id, max_pages=args.max_pages)
    else:
        run(args.config, out=args.out, since=args.since, until=args.until,
            min_chars=args.min_chars)


main()
