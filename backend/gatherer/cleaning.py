"""Normalisation shared by every source. Filtering spam/dupes is Checker's job, not ours;
we only make rows well-formed and drop ones with no usable text."""

import hashlib
import html
import re
from typing import Optional

import pandas as pd

from .schema import Review

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def clean_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = html.unescape(str(value))
    text = _TAG.sub(" ", text)
    return _WS.sub(" ", text).strip()


def parse_date(value) -> Optional[pd.Timestamp]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        # unix seconds vs milliseconds
        unit = "ms" if value > 1e11 else "s"
        ts = pd.to_datetime(value, unit=unit, errors="coerce", utc=True)
    else:
        ts = pd.to_datetime(value, errors="coerce", utc=True, format="mixed")
    return None if pd.isna(ts) else ts


def normalise_rating(value, scale: float = 5.0) -> Optional[float]:
    """Map any numeric rating onto 1-5. Accepts '4', '4.0', '4 out of 5', '8/10'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:/|out of)\s*(\d+(?:\.\d+)?)", value)
        if m:
            value, scale = float(m.group(1)), float(m.group(2))
        else:
            m = re.search(r"\d+(?:\.\d+)?", value)
            if not m:
                return None
            value = float(m.group())
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if scale != 5:
        value = 1 + (value / scale) * 4 if value <= scale else None
    if value is None or not 0 <= value <= 5:
        return None
    return round(max(value, 1.0), 2)


def make_id(r: Review) -> str:
    key = "|".join([r.source, r.business, r.author, r.date or "", r.text])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def finalise(r: Review, min_chars: int = 1) -> Optional[Review]:
    """Clean one review in place; return None if it has no usable text."""
    r.text = clean_text(r.text)
    r.title = clean_text(r.title)
    r.author = clean_text(r.author)
    if len(r.text) < min_chars:
        return None
    ts = parse_date(r.date)
    if ts is not None:
        r.date = ts.strftime("%Y-%m-%d")
        iso = ts.isocalendar()
        r.week = f"{iso.year}-W{iso.week:02d}"
    else:
        r.date, r.week = "", ""
    r.id = make_id(r)
    return r
