"""Kaggle / offline CSV datasets. This is the prototype stand-in for scraping.

Column names differ across every Kaggle dump, so we auto-detect them from the
candidate lists below; pass `columns={...}` to override any guess.
"""

import hashlib
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

import pandas as pd

from ..cleaning import normalise_rating
from ..schema import Review, OWN, MARKET
from .base import Source

# field -> header names seen in common Kaggle review datasets (compared lowercase,
# with spaces/underscores/dashes stripped)
CANDIDATES = {
    "text": ["reviewtext", "review", "reviewbody", "content", "text", "body", "comment",
             "comments", "feedback", "customerfeedback", "translatedreview", "reviewcontent", "description"],
    "rating": ["rating", "score", "stars", "overall", "reviewrating", "starrating",
               "ratingvalue", "userrating", "rate"],
    "date": ["date", "reviewdate", "at", "time", "timestamp", "createdat", "unixreviewtime",
             "reviewtime", "datetime", "publisheddate", "dateofreview", "posteddate"],
    "title": ["title", "summary", "reviewtitle", "headline", "subject"],
    "author": ["author", "username", "reviewername", "user", "name", "profilename", "reviewer",
               "customerid", "userid", "reviewerid"],
    "url": ["url", "link", "reviewurl"],
    "business": ["app", "appname", "product", "productname", "brand", "company", "business",
                 "businessname", "hotel", "hotelname", "restaurant", "name_of_product", "asin"],
}


def _key(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def detect_columns(headers) -> dict:
    """Best-guess mapping {field: header} for the given CSV headers."""
    by_key = {_key(h): h for h in headers}
    mapping, used = {}, set()
    for field, names in CANDIDATES.items():
        for n in names:
            h = by_key.get(_key(n))
            if h is not None and h not in used:
                mapping[field] = h
                used.add(h)
                break
    return mapping


class CsvSource(Source):
    kind = "csv"

    def __init__(self, path=None, business: str | None = None, origin: str = OWN,
                 columns: dict | None = None, rating_scale: float = 5.0,
                 business_column: str | None = None, own_values: list | None = None,
                 where: dict | None = None, source_name: str | None = None,
                 limit: int | None = None, kaggle: str | None = None,
                 file: str | None = None, keep: list | dict | None = None,
                 simulate_dates: dict | None = None, **read_csv_kwargs):
        """
        kaggle + file: pull `file` from Kaggle dataset `kaggle` (owner/slug) via kagglehub
            instead of giving a local `path`. Cached after the first download.
        keep: extra source columns to carry into the output, as a list or
            {output_name: source_column}. Checker ignores them; Analyst can segment on them.
        simulate_dates: {"weeks": 12, "end": "YYYY-MM-DD"} for datasets with no date
            column. Each row gets a fixed pseudo-random date in that window (same row ->
            same date every run) and `date_simulated` = True, so it's never mistaken for
            a real timestamp.
        business_column + own_values: for one CSV holding many products (e.g. a Kaggle
            dump of 50 apps). Rows whose business is in own_values become OWN, the rest
            MARKET. Leave own_values empty to treat every row as `origin`.
        where: {column: value or [values]} row filter applied before mapping.
        """
        super().__init__(business or "", origin, limit)
        if kaggle:
            import kagglehub
            path = Path(kagglehub.dataset_download(kaggle)) / (file or "")
        if path is None:
            raise ValueError("CsvSource needs `path` or `kaggle` + `file`")
        self.path = Path(path)
        self.keep = keep if isinstance(keep, dict) else {c: c for c in (keep or [])}
        self.simulate_dates = simulate_dates
        self.columns = columns or {}
        self.rating_scale = rating_scale
        self.business_column = business_column
        self.own_values = {str(v).lower() for v in (own_values or [])}
        self.where = where or {}
        self.source_name = source_name or f"kaggle:{self.path.stem}"
        self.read_csv_kwargs = {"low_memory": False, **read_csv_kwargs}

    def __repr__(self):
        return f"CsvSource({self.path.name!r}, origin={self.origin!r})"

    def load_frame(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.path, **self.read_csv_kwargs)
        except UnicodeDecodeError:
            df = pd.read_csv(self.path, encoding="latin-1", **self.read_csv_kwargs)
        for col, val in self.where.items():
            vals = val if isinstance(val, list) else [val]
            df = df[df[col].isin(vals)]
        return df

    def mapping(self, headers) -> dict:
        m = detect_columns(headers)
        m.update(self.columns)
        if self.business_column:
            m["business"] = self.business_column
        if "text" not in m:
            raise ValueError(
                f"{self.path.name}: couldn't find a review-text column in {list(headers)}. "
                f"Pass columns={{'text': '<header>'}}."
            )
        return m

    def fetch(self) -> Iterator[Review]:
        df = self.load_frame()
        m = self.mapping(df.columns)
        if self.limit:
            df = df.head(self.limit)
        get = lambda row, f: row.get(m[f]) if f in m else None

        if self.simulate_dates and "date" in m:
            raise ValueError(f"{self.path.name} has a date column; don't simulate_dates")

        for row in df.to_dict("records"):
            business = self.business
            origin = self.origin
            if "business" in m and (self.business_column or not business):
                business = str(get(row, "business") or business)
                if self.own_values:
                    origin = OWN if business.lower() in self.own_values else MARKET
            extra = {out: row.get(col) for out, col in self.keep.items()}
            text = get(row, "text")
            when = get(row, "date")
            if self.simulate_dates:
                when = self._fake_date(f"{get(row, 'author')}|{text}")
                extra["date_simulated"] = True
            yield Review(
                source=self.source_name,
                origin=origin,
                business=business,
                text=text,
                date=when,
                rating=normalise_rating(get(row, "rating"), self.rating_scale),
                title=get(row, "title") or "",
                author=get(row, "author") or "",
                url=get(row, "url") or "",
                extra=extra,
            )

    def _fake_date(self, key: str) -> str:
        weeks = self.simulate_dates.get("weeks", 12)
        end = date.fromisoformat(self.simulate_dates.get("end", date.today().isoformat()))
        offset = int(hashlib.sha1(key.encode()).hexdigest(), 16) % (weeks * 7)
        return (end - timedelta(days=offset)).isoformat()

