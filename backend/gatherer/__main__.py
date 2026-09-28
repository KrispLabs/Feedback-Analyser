"""CLI. Run from backend/:

  python -m gatherer --config gatherer_config.json
  python -m gatherer --config gatherer_config.json --since 2026-01-01 --min-chars 3
  python -m gatherer inspect ../data/raw/*.csv
"""

import argparse
from pathlib import Path

from .gatherer import DEFAULT_OUT, run
from .inspect_csv import inspect


def main():
    ap = argparse.ArgumentParser(prog="gatherer")
    sub = ap.add_subparsers(dest="cmd")

    ins = sub.add_parser("inspect", help="profile raw CSVs and suggest a column mapping")
    ins.add_argument("paths", nargs="+")
    ins.add_argument("--rows", type=int, default=3)

    ap.add_argument("--config", default="gatherer_config.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--since", help="keep reviews on/after YYYY-MM-DD")
    ap.add_argument("--until", help="keep reviews on/before YYYY-MM-DD")
    ap.add_argument("--min-chars", type=int, default=1)
    args = ap.parse_args()

    if args.cmd == "inspect":
        for p in args.paths:
            inspect(p, sample_rows=args.rows)
    else:
        run(args.config, out=args.out, since=args.since, until=args.until,
            min_chars=args.min_chars)


main()
