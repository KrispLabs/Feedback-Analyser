"""Demo: prove the Analyst's reasoning gets trend-aware across batches of
REAL gathered data, backed by Hindsight recall. Uses a dedicated bank
(separate from the production bank in memory.py) so this demo is never
contaminated by earlier mock/test memories."""

import json
import sys

import pandas as pd

from analyst import analyze_week
from checker import check_reviews
from gatherer.gatherer import DEFAULT_OUT
from gatherer.schema import OWN
from memory import HindsightMemory
from run_week import default_business
from scorer import extract_themes

DEMO_BANK_ID = "feedback-analyser-real-demo-v4"


def load_all_sorted(business: str) -> list[dict]:
    df = pd.read_csv(DEFAULT_OUT, dtype=str)
    df = df[(df["origin"] == OWN) & (df["business"] == business)]  # never competitors
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.sort_values("date")  # oldest first: real chronological order
    return df.to_dict("records")


def run_batch(batch_number: int, reviews: list[dict], memory: HindsightMemory) -> dict:
    verified, rejected_count, rejected_by_reason = check_reviews(reviews)
    themes = extract_themes(verified, rejected_count)
    analyzed = analyze_week(themes, memory, business=memory.business)
    result = {
        "batch": batch_number,
        "input_reviews": len(reviews),
        "rejected_count": rejected_count,
        "rejected_by_reason": rejected_by_reason,
        "themes": analyzed,
    }
    memory.store_week(batch_number, result)
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    business = default_business()
    all_reviews = load_all_sorted(business)

    batch_1 = all_reviews[:300]
    batch_2 = all_reviews[300:300 + 550]

    with HindsightMemory(business, bank_id=DEMO_BANK_ID) as memory:
        print(f"=== Batch 1: {len(batch_1)} reviews (clean bank, no prior history) ===")
        result_1 = run_batch(1, batch_1, memory)
        print(json.dumps(result_1, indent=2))

        print(f"\n=== Batch 2: {len(batch_2)} reviews (Analyst can now recall batch 1) ===")
        result_2 = run_batch(2, batch_2, memory)
        print(json.dumps(result_2, indent=2))
