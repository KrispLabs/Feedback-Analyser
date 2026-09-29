import csv
import os
from pathlib import Path

KEYS_CSV = Path(__file__).resolve().parent.parent / "keys.csv"

REQUIRED_KEYS = ["GROQ_API_KEY", "HINDSIGHT_API_KEY"]


def _csv_keys() -> dict:
    if not KEYS_CSV.exists():
        return {}
    with open(KEYS_CSV, newline="", encoding="utf-8") as f:
        return {row["key_name"]: row["value"] for row in csv.DictReader(f) if row["value"]}


def get_key(name: str) -> str | None:
    """Optional key lookup: environment first, then keys.csv. Returns None when
    unset, unlike load_keys() -- for keys only some sources need (e.g. the
    Gatherer's shop providers) so a missing one fails at use, not at import."""
    return os.environ.get(name) or _csv_keys().get(name)


def load_keys():
    """Prefer real environment variables (e.g. set via Docker/.env), fall back
    to keys.csv for local dev outside a container."""
    keys = {name: os.environ[name] for name in REQUIRED_KEYS if os.environ.get(name)}

    if len(keys) < len(REQUIRED_KEYS):
        for name, value in _csv_keys().items():
            keys.setdefault(name, value)
        keys = {k: v for k, v in keys.items() if k in REQUIRED_KEYS}

    missing = [name for name in REQUIRED_KEYS if name not in keys]
    if missing:
        raise RuntimeError(
            f"Missing API key(s): {', '.join(missing)}. "
            "Set them as environment variables (see .env.example) or in keys.csv."
        )
    return keys
