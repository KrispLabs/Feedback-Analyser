"""Reviews for one physical shop, found by name + location.

This is the branch of the Gatherer that covers shops rather than apps: give it
"Chai Point" + "Banjara Hills, Hyderabad" and it resolves the place, pulls its
Google reviews, and hands them downstream in the same Review shape as every
other source.

Two providers, picked with `provider`:
  places   Google Places API (New). Official and free-tier friendly, but Google
           only ever returns 5 reviews per place -- enough to prove the pipeline
           end to end, too thin to demo on. Needs GOOGLE_MAPS_API_KEY.
  serpapi  SerpApi's Google Maps scraper. Paginates through hundreds of reviews
           per shop with real ratings. 100 free searches/month. Needs
           SERPAPI_API_KEY.

Stdlib only (same as appstore.py) -- no new dependency for either provider.
Keys come from the env var, keys.csv, or an `api_key` in the source config.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Iterator

from ..schema import Review, OWN
from .base import Source

PLACES_SEARCH = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS = "https://places.googleapis.com/v1/places/{place_id}"
SERPAPI = "https://serpapi.com/search.json"

KEY_ENV = {"places": "GOOGLE_MAPS_API_KEY", "serpapi": "SERPAPI_API_KEY"}

# our sort names -> what each provider calls them
SERPAPI_SORT = {"newest": "newestFirst", "relevant": "qualityScore",
                "highest": "ratingHigh", "lowest": "ratingLow"}

TIMEOUT = 30

# Page 1 is always 8 results; SerpApi rejects `num` there but accepts up to 20
# on later pages, so pages 2+ cost the same one search for twice the reviews.
PAGE_SIZE = 20
# Every page is one billable SerpApi search, and a shop whose reviews are mostly
# star-only ratings can otherwise paginate a long way to reach `limit`. Stop
# here regardless, so one run can't quietly eat a monthly quota.
MAX_PAGES = 15

# SerpApi falls back to "a month ago" phrasing when a review has no iso_date.
_RELATIVE = re.compile(r"(?:(\d+)|an?)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)
_DAYS_PER = {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}


def parse_relative_date(value: str, today: date | None = None) -> str | None:
    """'3 months ago' -> ISO date, approximately. Approximate is the right call
    here: run_week() only ever buckets by ISO week, and a review dated to the
    right fortnight is far more useful than one with no date at all (those get
    an empty `week` and drop out of every weekly run)."""
    match = _RELATIVE.search(value or "")
    if not match:
        return None
    amount = int(match.group(1)) if match.group(1) else 1
    days = amount * _DAYS_PER[match.group(2).lower()]
    return ((today or date.today()) - timedelta(days=days)).isoformat()


class ShopSource(Source):
    kind = "shop"

    def __init__(self, name: str, location: str = "", business: str | None = None,
                 origin: str = OWN, limit: int = 100, provider: str = "places",
                 api_key: str | None = None, language: str = "en",
                 sort: str = "newest", place_id: str | None = None,
                 max_pages: int = MAX_PAGES, since: str | None = None):
        """
        name + location: what you'd type into Google Maps, e.g. "Chai Point",
            "Banjara Hills, Hyderabad". Joined into one query and resolved to a
            single place -- the first hit, same as Maps' own "I'm feeling lucky".
        place_id: skip the lookup and go straight to this place. Use it when the
            name is ambiguous (three branches in one city) and the search keeps
            resolving to the wrong branch.
        limit: stop after this many reviews **that have review text**. Star-only
            ratings carry no text, get dropped downstream, and are useless to the
            Checker, so they don't count against it -- on Google Maps they're most
            of what a page returns.
        max_pages: hard ceiling on billable SerpApi searches for this shop.
        since: ISO date (YYYY-MM-DD); keep only reviews on/after it. With the
            default newest-first sort, pagination also STOPS once a whole page
            predates it -- a popular shop with years of history then costs a
            few searches instead of the full max_pages. Requires sort="newest";
            any other sort only filters, since order says nothing about dates.
        """
        super().__init__(business or name, origin, limit)
        if provider not in KEY_ENV:
            raise ValueError(f"provider must be one of {sorted(KEY_ENV)}, got {provider!r}")
        if sort not in SERPAPI_SORT:
            raise ValueError(f"sort must be one of {sorted(SERPAPI_SORT)}, got {sort!r}")
        self.name = name
        self.location = location
        self.provider = provider
        self.api_key = api_key
        self.language = language
        self.sort = sort
        self.place_id = place_id
        self.max_pages = max_pages
        self.since = since
        self.pages_fetched = 0  # billable searches used, for the caller to report

    @property
    def query(self) -> str:
        return f"{self.name}, {self.location}".strip().strip(",")

    def __repr__(self):
        return f"ShopSource({self.query!r}, via={self.provider!r}, origin={self.origin!r})"

    # --- plumbing -----------------------------------------------------------

    def _key(self) -> str:
        env_var = KEY_ENV[self.provider]
        key = self.api_key or os.environ.get(env_var)
        if not key:
            try:  # keys.csv, how the team runs it outside Docker
                from config import get_key
                key = get_key(env_var)
            except ImportError:
                pass
        if not key:
            raise RuntimeError(
                f"provider {self.provider!r} needs {env_var} -- set it as an environment "
                f"variable (see .env.example), add it to keys.csv, or pass api_key in the config."
            )
        return key

    @staticmethod
    def _request(url: str, headers: dict | None = None, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "Mozilla/5.0", **({"Content-Type": "application/json"} if data else {}),
            **(headers or {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            # both APIs put the useful part ("API key not valid", quota) in the body
            detail = e.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"{e.code} from {urllib.parse.urlsplit(url).netloc}: {detail}") from e

    def _serpapi_get(self, **params) -> dict:
        url = f"{SERPAPI}?" + urllib.parse.urlencode({"hl": self.language, **params})
        payload = self._request(url)
        if payload.get("error"):
            raise RuntimeError(f"serpapi: {payload['error']}")
        return payload

    def fetch(self) -> Iterator[Review]:
        return self._serpapi() if self.provider == "serpapi" else self._places()

    # --- providers ----------------------------------------------------------

    def _places(self) -> Iterator[Review]:
        key = self._key()
        place_id = self.place_id
        if not place_id:
            found = self._request(
                PLACES_SEARCH,
                headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"},
                body={"textQuery": self.query, "maxResultCount": 1, "languageCode": self.language},
            ).get("places") or []
            if not found:
                raise RuntimeError(f"no place matched {self.query!r} -- try a fuller address, "
                                   f"or pass place_id directly")
            place_id = found[0]["id"]

        details = self._request(
            PLACES_DETAILS.format(place_id=place_id) + "?" + urllib.parse.urlencode(
                {"languageCode": self.language}),
            headers={"X-Goog-Api-Key": key,
                     "X-Goog-FieldMask": "reviews,rating,userRatingCount,formattedAddress"},
        )
        shop = {"place_id": place_id,
                "shop_address": details.get("formattedAddress", ""),
                "shop_rating": details.get("rating"),
                "shop_review_count": details.get("userRatingCount")}

        kept = 0
        for review in details.get("reviews") or []:
            if kept >= self.limit:
                return
            body = review.get("text") or review.get("originalText") or {}
            if not (body.get("text") or "").strip():
                continue
            if self.since and (review.get("publishTime") or "")[:10] < self.since:
                continue
            kept += 1
            yield Review(
                source="google_places",
                origin=self.origin,
                business=self.business,
                text=body.get("text"),
                date=review.get("publishTime"),
                rating=review.get("rating"),
                author=(review.get("authorAttribution") or {}).get("displayName", ""),
                url=review.get("googleMapsUri", ""),
                extra=dict(shop),
            )

    def _serpapi(self) -> Iterator[Review]:
        key = self._key()
        data_id = self.place_id
        if not data_id:
            found = self._serpapi_get(engine="google_maps", type="search", q=self.query, api_key=key)
            place = found.get("place_results") or (found.get("local_results") or [{}])[0]
            data_id = place.get("data_id")
            if not data_id:
                raise RuntimeError(f"no place matched {self.query!r} -- try a fuller address, "
                                   f"or pass place_id (the Maps data_id) directly")
            shop = {"place_id": data_id,
                    "shop_address": place.get("address", ""),
                    "shop_rating": place.get("rating"),
                    "shop_review_count": place.get("reviews")}
        else:
            shop = {"place_id": data_id}

        token, yielded = None, 0
        while yielded < self.limit and self.pages_fetched < self.max_pages:
            params = {"engine": "google_maps_reviews", "data_id": data_id, "api_key": key,
                      "sort_by": SERPAPI_SORT[self.sort]}
            if token:  # rejected on page 1, which is always 8 results
                params["next_page_token"] = token
                params["num"] = PAGE_SIZE
            page = self._serpapi_get(**params)
            self.pages_fetched += 1

            reviews = page.get("reviews") or []
            if not reviews:
                break
            page_all_older = bool(self.since)
            for review in reviews:
                # star-only rating with no text: nothing for the Checker or the
                # Scorer to read, so skip it rather than spend `limit` on it
                if not (review.get("snippet") or "").strip():
                    continue
                when = review.get("iso_date") or review.get("iso_date_of_last_edit")
                extra = dict(shop)
                if not when:
                    when = parse_relative_date(review.get("date", ""))
                    extra["date_approx"] = True  # derived from "3 months ago", not exact
                if self.since and when:
                    if when[:10] < self.since:
                        continue          # older than the window: drop it
                    page_all_older = False  # something on this page is in range
                user = review.get("user") or {}
                yield Review(
                    source="google_maps",
                    origin=self.origin,
                    business=self.business,
                    text=review.get("snippet") or review.get("extracted_snippet", {}).get("original"),
                    date=when,
                    rating=review.get("rating"),
                    author=user.get("name", ""),
                    url=review.get("link", ""),
                    extra={**extra, "likes": review.get("likes")},
                )
                yielded += 1
                if yielded >= self.limit:
                    return

            # newest-first: once an entire page predates the window, everything
            # after it does too, so stop paying for pages we would only discard
            if page_all_older and self.sort == "newest":
                break
            token = (page.get("serpapi_pagination") or {}).get("next_page_token")
            if not token:
                break
