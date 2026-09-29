"""Lead: Hindsight Cloud integration. Stores each week's result and recalls
past weeks so the Analyst can reason about trends across weeks.

Every memory is scoped to one business. The bank is shared by every flow
(run_week's Telco weeks, every shop analyse_shop looks up), and before this
scoping a recall for "Overpriced chai at Niloufer Cafe" came back with 26 Telco
memories, which the Analyst then cited as the cafe's "past trend". Now each
retain is tagged `business:<slug>` and recall filters on that tag with
any_strict, which also excludes the older untagged memories.

Memory is an enhancement, not a dependency: if Hindsight is down or its key is
missing, the analysis still runs -- the Analyst just gets no past context and
nothing is stored. `error` says why, for the caller to surface as a warning.
It used to raise, after SerpApi and Groq had already been paid for."""

import hashlib
import json
import os
import re
from datetime import datetime

from hindsight_client import Hindsight

from config import get_key

# "feedback-analyser" holds Phase 1-4 mock test memories (fake "login issues"/
# "dark mode" data) that contaminate recall for real weeks -- see NOTES.md. v2
# starts clean; never repoint production at v1. HINDSIGHT_BANK_ID overrides it
# for experiments (scorer comparisons, demos) so they never write into the
# production bank -- which is how that contamination got in twice already.
BANK_ID = os.environ.get("HINDSIGHT_BANK_ID", "feedback-analyser-v2")
BASE_URL = "https://api.hindsight.vectorize.io"


def business_tag(business: str) -> str:
    """'Niloufer Cafe, Hitech City' -> 'business:niloufer-cafe-hitech-city'.

    The slug keeps only a-z0-9, so a name in another script ("चाय वाला, Hitech
    City") used to raise -- after every paid call -- or would reduce to just
    its location and share a history with every such shop there. Names with
    any non-ASCII letters get a short hash of the full name appended; plain
    ASCII names keep their existing tags."""
    slug = re.sub(r"[^a-z0-9]+", "-", business.lower()).strip("-")
    if slug and business.isascii():
        return f"business:{slug}"
    digest = hashlib.sha1(business.strip().lower().encode("utf-8")).hexdigest()[:10]
    return f"business:{slug + '-' if slug else ''}{digest}"


class HindsightMemory:
    def __init__(self, business: str, bank_id: str = BANK_ID):
        """business: whose memories these are. Required on purpose -- an unscoped
        memory is how one business's history leaked into another's analysis."""
        self.bank_id = bank_id
        self.business = business
        self.tag = business_tag(business)
        self.error: str | None = None
        self._client = None
        try:
            api_key = get_key("HINDSIGHT_API_KEY")
            if not api_key:
                raise RuntimeError("HINDSIGHT_API_KEY is not set")
            self._client = Hindsight(base_url=BASE_URL, api_key=api_key)
            self._client.create_bank(bank_id=bank_id, name=f"Feedback Analyser ({bank_id})")
        except Exception as e:
            self._disable(e)

    @property
    def available(self) -> bool:
        return self.error is None

    def _disable(self, e: Exception) -> None:
        """First failure turns memory off for the rest of this run: one
        timeout per theme would add minutes to a request that's already slow."""
        if self.error is None:
            self.error = f"Hindsight unavailable ({type(e).__name__}: {e})"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    def store_week(self, week_number: int, week_result: dict,
                   timestamp: datetime | None = None, run_key: str | None = None) -> bool:
        """week_result is the dict run_week() produces: themes (with scores,
        sample reviews) and the Analyst's reasoning/next-steps per theme.

        timestamp: when the reviews are from, not when we ran. Without it
        Hindsight dates every memory "today", so replaying twelve past weeks
        would look like twelve analyses of this week.

        run_key: identifies this run within the business (default "week:<n>").
        Storing the same key again REPLACES the earlier memory, so re-running a
        week no longer stacks duplicates that read as "3 runs straight".

        Themes the Analyst couldn't really score (degraded: Groq down, or an
        unparseable reply) are left out -- stored, their placeholder 0 came back
        on the next run as a genuine past trend. Returns False, storing nothing,
        when no theme was really scored."""
        if not self.available:
            return False
        themes = week_result.get("themes", [])
        real = [{k: v for k, v in t.items() if k != "degraded"}
                for t in themes if not t.get("degraded")]
        if not real:
            return False
        skipped = len(themes) - len(real)
        content = (
            f"{self.business} -- week {week_number} feedback analysis.\n"
            f"Period: {week_result.get('period', 'unknown')}\n"
            f"Rejected reviews: {week_result.get('rejected_count', 0)}\n"
            + (f"({skipped} more themes could not be scored and are omitted)\n" if skipped else "")
            + json.dumps(real, indent=2)
        )
        try:
            self._client.retain(
                bank_id=self.bank_id,
                content=content,
                timestamp=timestamp,
                context=f"{self.business}: week {week_number} feedback synthesis",
                document_id=f"{self.tag}:{run_key or f'week:{week_number}'}",
                update_mode="replace",
                tags=[self.tag, f"week:{week_number}"],
                metadata={"business": self.business, "week": str(week_number)},
            )
        except Exception as e:
            self._disable(e)
            return False
        return True

    def recall_context(self, query: str, budget: str = "mid",
                       before_week: int | None = None) -> list[str]:
        """Returns this business's past memory text relevant to the query, for
        the Analyst to reason over trends (e.g. a theme recurring across weeks).

        before_week: drop memories tagged with this week or a later one.
        Re-running week 3 after weeks 1-12 are stored otherwise hands the
        Analyst weeks 4-12 -- and week 3's own old result -- as "the past"."""
        if not self.available:
            return []
        try:
            result = self._client.recall(bank_id=self.bank_id, query=query, budget=budget,
                                         tags=[self.tag], tags_match="any_strict")
        except Exception as e:
            self._disable(e)
            return []
        return [memory.text for memory in result.results
                if before_week is None or _week_of(memory.tags) < before_week]


def _week_of(tags: list[str] | None) -> float:
    """The week:<n> tag's number; -inf for untagged memories, so they're kept."""
    for tag in tags or []:
        if tag.startswith("week:") and tag[5:].isdigit():
            return int(tag[5:])
    return float("-inf")


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
