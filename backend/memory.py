"""Lead: Hindsight Cloud integration. Stores each week's result and recalls
past weeks so the Analyst can reason about trends across weeks."""

import json

from hindsight_client import Hindsight

from config import load_keys

BANK_ID = "feedback-analyser-v2"  # "feedback-analyser" holds Phase 1-4 mock test
# memories (fake "login issues"/"dark mode" data) that contaminate recall for
# real weeks -- see NOTES.md. v2 starts clean; never repoint this at v1.
BASE_URL = "https://api.hindsight.vectorize.io"


class HindsightMemory:
    def __init__(self, bank_id: str = BANK_ID):
        keys = load_keys()
        self.bank_id = bank_id
        self._client = Hindsight(base_url=BASE_URL, api_key=keys["HINDSIGHT_API_KEY"])
        self._client.create_bank(bank_id=bank_id, name=f"Feedback Analyser ({bank_id})")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._client.close()

    def store_week(self, week_number: int, week_result: dict):
        """week_result is the dict run_week() produces: themes (with scores,
        sample reviews) and the Analyst's reasoning/next-steps per theme."""
        content = (
            f"Week {week_number} feedback analysis.\n"
            f"Rejected reviews: {week_result.get('rejected_count', 0)}\n"
            f"{json.dumps(week_result.get('themes', []), indent=2)}"
        )
        self._client.retain(
            bank_id=self.bank_id,
            content=content,
            context=f"Week {week_number} feedback synthesis",
            tags=[f"week:{week_number}"],
            metadata={"week": str(week_number)},
        )

    def recall_context(self, query: str, budget: str = "mid") -> list[str]:
        """Returns past memory text relevant to the query, for the Analyst to
        reason over trends (e.g. a theme recurring across weeks)."""
        result = self._client.recall(bank_id=self.bank_id, query=query, budget=budget)
        return [memory.text for memory in result.results]


if __name__ == "__main__":
    # A dedicated test bank -- NEVER the default/production bank here. Running
    # this file previously wrote a fake "login issues" memory straight into
    # feedback-analyser-v2, contaminating real recall the same way the
    # original feedback-analyser bank was contaminated (see NOTES.md).
    TEST_BANK_ID = "feedback-analyser-selftest"

    with HindsightMemory(bank_id=TEST_BANK_ID) as memory:
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
