from .base import Source
from .csv_source import CsvSource, detect_columns
from .playstore import PlayStoreSource
from .appstore import AppStoreSource
from .shop import ShopSource

REGISTRY = {cls.kind: cls for cls in (CsvSource, PlayStoreSource, AppStoreSource, ShopSource)}

__all__ = ["Source", "CsvSource", "PlayStoreSource", "AppStoreSource", "ShopSource",
           "REGISTRY", "detect_columns"]
