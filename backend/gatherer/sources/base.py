import ssl
from typing import Iterator

from ..schema import Review, OWN, MARKET

# For sources that fetch with urllib. Python from the python.org macOS
# installer ships without root certificates until "Install Certificates" is
# run, so every HTTPS call failed with CERTIFICATE_VERIFY_FAILED outside
# Docker. certifi (already installed with groq) carries its own bundle.
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()


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
