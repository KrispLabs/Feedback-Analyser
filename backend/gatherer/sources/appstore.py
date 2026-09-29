"""Live Apple App Store reviews from Apple's public customer-reviews RSS feed.

Stdlib only. The feed serves up to 10 pages x 50 most recent reviews per country.
"""

import json
import urllib.request
from typing import Iterator

from ..schema import Review, OWN
from .base import SSL_CONTEXT, Source

FEED = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"


class AppStoreSource(Source):
    kind = "appstore"

    def __init__(self, app_id: str | int, business: str | None = None, origin: str = OWN,
                 limit: int = 200, country: str = "in"):
        super().__init__(business or str(app_id), origin, limit)
        self.app_id, self.country = str(app_id), country

    def _page(self, page: int) -> list:
        url = FEED.format(country=self.country, page=page, app_id=self.app_id)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CONTEXT) as resp:
            feed = json.load(resp).get("feed", {})
        entries = feed.get("entry", [])
        if isinstance(entries, dict):  # a single entry isn't wrapped in a list
            entries = [entries]
        return [e for e in entries if "im:rating" in e]  # page 1 can lead with app metadata

    def fetch(self) -> Iterator[Review]:
        count = 0
        for page in range(1, 11):
            entries = self._page(page)
            if not entries:
                break
            for e in entries:
                yield Review(
                    source="appstore",
                    origin=self.origin,
                    business=self.business,
                    text=e.get("content", {}).get("label"),
                    title=e.get("title", {}).get("label", ""),
                    date=e.get("updated", {}).get("label"),
                    rating=float(e["im:rating"]["label"]),
                    author=e.get("author", {}).get("name", {}).get("label", ""),
                    url=e.get("link", {}).get("attributes", {}).get("href", ""),
                    extra={"app_version": e.get("im:version", {}).get("label")},
                )
                count += 1
                if count >= self.limit:
                    return
