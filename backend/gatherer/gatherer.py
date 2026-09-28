"""Feedback Gatherer: pulls reviews from every configured source and writes one cleaned table.

Two branches, matching the flow diagram:
  own    -> real feedback about the business from review sites / datasets
  market -> feedback about similar products in the same market

Config (JSON):
{
  "business": "Spotify",
  "own":    [{"type": "playstore", "app_id": "com.spotify.music"}],
  "market": [{"type": "csv", "path": "../data/raw/music_apps.csv",
              "business_column": "app"}]
}
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd

from .cleaning import finalise
from .schema import COLUMNS, OWN, MARKET
from .sources import REGISTRY, Source

# repo-root data/ locally; docker-compose sets DATA_DIR=/data and mounts ./data there
DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
DEFAULT_OUT = DATA_DIR / "cleaned" / "reviews.csv"


def build_sources(config: dict, base_dir: Path | None = None) -> list[Source]:
    business = config.get("business", "")
    sources = []
    for origin in (OWN, MARKET):
        for spec in config.get(origin, []):
            spec = dict(spec)
            kind = spec.pop("type")
            if kind not in REGISTRY:
                raise ValueError(f"unknown source type {kind!r}; known: {sorted(REGISTRY)}")
            if kind == "csv" and base_dir and "path" in spec and not Path(spec["path"]).is_absolute():
                spec["path"] = base_dir / spec["path"]
            spec.setdefault("origin", origin)
            if origin == OWN:
                spec.setdefault("business", business)
            sources.append(REGISTRY[kind](**spec))
    return sources


def gather(sources: list[Source], min_chars: int = 1, since: str | None = None,
           until: str | None = None, log=print) -> pd.DataFrame:
    rows = []
    for src in sources:
        fetched = kept = 0
        try:
            for raw in src.fetch():
                fetched += 1
                r = finalise(raw, min_chars=min_chars)
                if r is not None:
                    rows.append({**r.row(), **{k: v for k, v in r.extra.items() if k not in COLUMNS}})
                    kept += 1
        except Exception as e:  # one dead source shouldn't kill the week's run
            log(f"  ! {src!r} failed: {e}")
        log(f"  {src!r}: fetched {fetched}, kept {kept}"
            + ("  <- nothing returned, check the id/path" if fetched == 0 else ""))

    extras = list(dict.fromkeys(k for row in rows for k in row if k not in COLUMNS))
    df = pd.DataFrame(rows, columns=COLUMNS + extras)
    # identical review pulled twice from the same source (overlapping pages / reruns)
    df = df.drop_duplicates(subset="id")
    if since:
        df = df[df["date"] >= since]
    if until:
        df = df[(df["date"] <= until) & (df["date"] != "")]
    return df.sort_values(["date", "source"], ascending=[False, True]).reset_index(drop=True)


def load(path: Path = DEFAULT_OUT, week: str | None = None, origin: str | None = None) -> pd.DataFrame:
    """Read the cleaned table back, optionally sliced to one ISO week / origin (for run_week)."""
    df = pd.read_csv(path, dtype={"id": str, "week": str, "date": str}, keep_default_na=False)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if week:
        df = df[df["week"] == week]
    if origin:
        df = df[df["origin"] == origin]
    return df


def summarise(df: pd.DataFrame) -> str:
    if df.empty:
        return "no reviews gathered"
    lines = [f"{len(df)} reviews"]
    for (origin, business), g in df.groupby(["origin", "business"]):
        dated = g[g["date"] != ""]["date"]
        span = f"{dated.min()} .. {dated.max()}" if len(dated) else "no dates"
        avg = g["rating"].mean()
        lines.append(f"  [{origin}] {business}: {len(g)} reviews, avg rating "
                     f"{avg:.2f}, {span}" if pd.notna(avg) else
                     f"  [{origin}] {business}: {len(g)} reviews, no ratings, {span}")
    return "\n".join(lines)


def run(config_path: str, out: Path = DEFAULT_OUT, **kw) -> pd.DataFrame:
    config_path = Path(config_path)
    config = json.loads(config_path.read_text())
    sources = build_sources(config, base_dir=config_path.parent)
    print(f"Gathering for {config.get('business')!r} from {len(sources)} source(s)")
    df = gather(sources, **kw)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(summarise(df))
    print(f"-> {out}")
    return df


if __name__ == "__main__":
    sys.exit("run as: python -m gatherer --config <file.json>")
