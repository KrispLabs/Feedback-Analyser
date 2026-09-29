"""Live Google Play reviews via the google-play-scraper package (no API key needed)."""

from typing import Iterator

from ..schema import Review, OWN
from .base import Source


class PlayStoreSource(Source):
    kind = "playstore"

    def __init__(self, app_id: str, business: str | None = None, origin: str = OWN,
                 limit: int = 200, lang: str = "en", country: str = "in"):
        super().__init__(business or app_id, origin, limit)
        self.app_id, self.lang, self.country = app_id, lang, country

    def fetch(self) -> Iterator[Review]:
        try:
            from google_play_scraper import reviews, Sort
        except ImportError as e:
            raise RuntimeError("pip install google-play-scraper") from e

        result, _ = reviews(self.app_id, lang=self.lang, country=self.country,
                            sort=Sort.NEWEST, count=self.limit)
        for r in result:
            yield Review(
                source="playstore",
                origin=self.origin,
                business=self.business,
                text=r.get("content"),
                date=r.get("at"),
                rating=r.get("score"),
                author=r.get("userName") or "",
                url=f"https://play.google.com/store/apps/details?id={self.app_id}"
                    f"&reviewId={r.get('reviewId')}",
                extra={"thumbs_up": r.get("thumbsUpCount"), "app_version": r.get("appVersion")},
            )
