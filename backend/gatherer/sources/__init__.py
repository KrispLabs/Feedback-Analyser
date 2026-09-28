from .base import Source
from .csv_source import CsvSource, detect_columns
from .playstore import PlayStoreSource
from .appstore import AppStoreSource

REGISTRY = {cls.kind: cls for cls in (CsvSource, PlayStoreSource, AppStoreSource)}

__all__ = ["Source", "CsvSource", "PlayStoreSource", "AppStoreSource", "REGISTRY",
           "detect_columns"]
