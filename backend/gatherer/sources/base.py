from typing import Iterator

from ..schema import Review, OWN, MARKET


class Source:
    """A place reviews come from. Subclasses yield raw Review objects; cleaning happens later."""

    kind = "base"

    def __init__(self, business: str, origin: str = OWN, limit: int | None = None):
        if origin not in (OWN, MARKET):
            raise ValueError(f"origin must be '{OWN}' or '{MARKET}', got {origin!r}")
        self.business = business
        self.origin = origin
        self.limit = limit

    def fetch(self) -> Iterator[Review]:
        raise NotImplementedError

    def __repr__(self):
        return f"{type(self).__name__}(business={self.business!r}, origin={self.origin!r})"
