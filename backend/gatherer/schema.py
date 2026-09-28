"""The one row format every source is normalised into.

Checker contract (NOTES.md): id, source, date, rating, text. The extra columns
let the Analyst split own-product vs similar-market feedback and bucket by week.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional

OWN = "own"          # real feedback about the business itself
MARKET = "market"    # feedback about similar / competitor products

COLUMNS = [
    "id",        # stable hash, same review always gets the same id
    "source",    # e.g. playstore, appstore, kaggle:amazon_reviews
    "origin",    # OWN or MARKET
    "business",  # which product the review is about
    "date",      # ISO YYYY-MM-DD
    "week",      # ISO week, e.g. 2026-W39 (what run_week() slices on)
    "rating",    # float on a 1-5 scale, empty if the source has none
    "text",      # cleaned review body
    "title",
    "author",
    "url",
]


@dataclass
class Review:
    source: str
    origin: str
    business: str
    text: str
    date: Optional[str] = None
    rating: Optional[float] = None
    title: str = ""
    author: str = ""
    url: str = ""
    id: str = ""
    week: str = ""
    extra: dict = field(default_factory=dict)  # untouched source-specific fields

    def row(self):
        d = asdict(self)
        return {k: d[k] for k in COLUMNS}
