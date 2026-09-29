"""Profile a raw Kaggle CSV: shape, per-column type/nulls/examples, and the mapping
CsvSource would auto-detect. Use it to write the config entry for a new dataset."""

import json

import pandas as pd

from .sources.csv_source import detect_columns


def inspect(path, sample_rows: int = 3):
    try:
        df = pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, low_memory=False, encoding="latin-1")

    print(f"\n=== {path}")
    print(f"{len(df):,} rows x {len(df.columns)} columns\n")
    print(f"{'column':<28}{'dtype':<10}{'null%':>7}{'unique':>10}  example")
    for col in df.columns:
        s = df[col]
        example = s.dropna().astype(str).head(1).tolist()
        example = (example[0][:60] + "…") if example and len(example[0]) > 60 else (example[0] if example else "")
        print(f"{str(col)[:27]:<28}{str(s.dtype):<10}{s.isna().mean() * 100:>6.1f}%"
              f"{s.nunique():>10,}  {example!r}")

    mapping = detect_columns(df.columns)
    print("\nauto-detected mapping:", json.dumps(mapping))
    if "text" in mapping:
        lengths = df[mapping["text"]].dropna().astype(str).str.len()
        print(f"text length: median {lengths.median():.0f}, "
              f"<10 chars {(lengths < 10).mean() * 100:.1f}%")
    if "rating" in mapping:
        print("rating values:", df[mapping["rating"]].value_counts().head(10).to_dict())
    if "business" in mapping:
        top = df[mapping["business"]].value_counts().head(10)
        print(f"businesses ({df[mapping['business']].nunique()}):", top.to_dict())
    if "date" in mapping:
        d = pd.to_datetime(df[mapping["date"]], errors="coerce", utc=True, format="mixed")
        print(f"dates: {d.min()} .. {d.max()} ({d.isna().mean() * 100:.1f}% unparseable)")
    missing = [f for f in ("text", "rating", "date") if f not in mapping]
    if missing:
        print("NOT detected (set in config `columns`):", missing)
    print()
    print(df.head(sample_rows).to_string(max_colwidth=50))
