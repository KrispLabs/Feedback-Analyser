"""Lead: Hindsight Cloud integration. Stores each week's result and recalls
past weeks so the Analyst can reason about trends across weeks.

Every memory is scoped to one business. The bank is shared by every flow
(run_week's Telco weeks, every shop analyse_shop looks up), and before this
scoping a recall for "Overpriced chai at Niloufer Cafe" came back with 26 Telco
memories, which the Analyst then cited as the cafe's "past trend". Now each
retain is tagged `business:<slug>` and recall filters on that tag with
any_strict, which also excludes the older untagged memories."""

import json
import os
import re
from datetime import datetime

from hindsight_client import Hindsight

from config import load_keys

# "feedback-analyser" holds Phase 1-4 mock test memories (fake "login issues"/
# "dark mode" data) that contaminate recall for real weeks -- see NOTES.md. v2
# starts clean; never repoint production at v1. HINDSIGHT_BANK_ID overrides it
# for experiments (scorer comparisons, demos) so they never write into the
# production bank -- which is how that contamination got in twice already.
BANK_ID = os.environ.get("HINDSIGHT_BANK_ID", "feedback-analyser-v2")
BASE_URL = "https://api.hindsight.vectorize.io"


def business_tag(business: str) -> str:
    """'Niloufer Cafe, Hitech City' -> 'business:niloufer-cafe-hitech-city'."""
    slug = re.sub(r"[^a-z0-9]+", "-", business.lower()).strip("-")
    if not slug:
        raise ValueError(f"business name {business!r} has nothing to build a memory tag from")
    return f"business:{slug}"


class HindsightMemory:
    def __init__(self, business: str, bank_id: str = BANK_ID):
        """business: whose memories these are. Required on purpose -- an unscoped
        memory is how one business's history leaked into another's analysis."""
        keys = load_keys()
        self.bank_id = bank_id
        self.business = business
        self.tag = business_tag(business)
        self._client = Hindsight(base_url=BASE_URL, api_key=keys["HINDSIGHT_API_KEY"])
        self._client.create_bank(bank_id=bank_id, name=f"Feedback Analyser ({bank_id})")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._client.close()

    def store_week(self, week_number: int, week_result: dict,
                   timestamp: datetime | None = None):
        """week_result is the dict run_week() produces: themes (with scores,
        sample reviews) and the Analyst's reasoning/next-steps per theme.

        timestamp: when the reviews are from, not when we ran. Without it
        Hindsight dates every memory "today", so replaying twelve past weeks
        would look like twelve analyses of this week."""
        content = (
            f"{self.business} -- week {week_number} feedback analysis.\n"
            f"Period: {week_result.get('period', 'unknown')}\n"
            f"Rejected reviews: {week_result.get('rejected_count', 0)}\n"
            f"{json.dumps(week_result.get('themes', []), indent=2)}"
        )
        self._client.retain(
            bank_id=self.bank_id,
            content=content,
            timestamp=timestamp,
            context=f"{self.business}: week {week_number} feedback synthesis",
            tags=[self.tag, f"week:{week_number}"],
            metadata={"business": self.business, "week": str(week_number)},
        )

    def recall_context(self, query: str, budget: str = "mid") -> list[str]:
        """Returns this business's past memory text relevant to the query, for
        the Analyst to reason over trends (e.g. a theme recurring across weeks)."""
        result = self._client.recall(bank_id=self.bank_id, query=query, budget=budget,
                                     tags=[self.tag], tags_match="any_strict")
        return [memory.text for memory in result.results]


if __name__ == "__main__":
    # A dedicated test bank -- NEVER the default/production bank here. Running
    # this file previously wrote a fake "login issues" memory straight into
    # feedback-analyser-v2, contaminating real recall the same way the
    # original feedback-analyser bank was contaminated (see NOTES.md).
    TEST_BANK_ID = "feedback-analyser-selftest"

    with HindsightMemory("Selftest App", bank_id=TEST_BANK_ID) as memory:
        memory.store_week(
            1,
            {
                "rejected_count": 6,
                "themes": [
                    {
                        "name": "login issues",
                        "count": 3,
                        "sentiment": "negative",
                        "severity": 7,
                        "samples": ["App keeps crashing when I try to log in"],
                    }
                ],
            },
        )
        print("Recall test:")
        for text in memory.recall_context("What happened with login issues in week 1?"):
            print("-", text)
