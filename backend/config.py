import csv
from pathlib import Path

KEYS_CSV = Path(__file__).resolve().parent.parent / "keys.csv"


def load_keys():
    keys = {}
    with open(KEYS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["value"]:
                keys[row["key_name"]] = row["value"]
    return keys
