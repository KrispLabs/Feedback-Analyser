import csv
import os
from pathlib import Path

KEYS_CSV = Path(__file__).resolve().parent.parent / "keys.csv"

REQUIRED_KEYS = ["GROQ_API_KEY", "HINDSIGHT_API_KEY"]


def load_keys():
    """Prefer real environment variables (e.g. set via Docker/.env), fall back
    to keys.csv for local dev outside a container."""
    keys = {name: os.environ[name] for name in REQUIRED_KEYS if os.environ.get(name)}

    if len(keys) < len(REQUIRED_KEYS) and KEYS_CSV.exists():
        with open(KEYS_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["value"] and row["key_name"] not in keys:
                    keys[row["key_name"]] = row["value"]

    missing = [name for name in REQUIRED_KEYS if name not in keys]
    if missing:
        raise RuntimeError(
            f"Missing API key(s): {', '.join(missing)}. "
            "Set them as environment variables (see .env.example) or in keys.csv."
        )
    return keys
