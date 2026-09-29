"""Scorer: the sorter. Groups verified reviews into themes.

Numeric scoring (-5..+5) is the Analyst's job (see analyst.py), using
Hindsight-informed reasoning -- so this module only needs to return
[{"name", "count", "samples"}, ...] per the agreed interface (NOTES.md).

No separate Scorer teammate branch exists yet, so this discovers themes with
an LLM instead of a hardcoded keyword list, so it generalizes to any dataset
(Telco this week, a different business next week) rather than only the one
domain we happened to test against."""

import json
import random

from llm import call_llm

SAMPLE_SIZE = 60
MAX_THEMES = 5

DISCOVER_PROMPT = """You are grouping customer feedback into themes for a business.
Read the sample reviews below and identify up to {max_themes} recurring themes.
For each theme, give a short name (2-4 words) and 3-6 lowercase keywords or short
phrases that would appear in a review about that theme, so more reviews can be
matched to it later by simple text search.

Respond as ONLY a JSON object: {{"themes": [{{"name": str, "keywords": [str, ...]}}, ...]}}"""

FALLBACK = json.dumps({"themes": []})


def discover_themes(reviews: list[dict]) -> list[dict]:
    sample = random.sample(reviews, min(SAMPLE_SIZE, len(reviews)))
    sample_text = "\n".join(f"- {r['text'][:300]}" for r in sample)

    raw = call_llm(DISCOVER_PROMPT.format(max_themes=MAX_THEMES), sample_text, fallback=FALLBACK)
    try:
        return json.loads(raw).get("themes", [])
    except json.JSONDecodeError:
        return []


def score_themes(verified_reviews: list[dict]) -> list[dict]:
    """Returns [{"name", "count", "samples"}, ...]."""
    if not verified_reviews:
        return []

    themes = []
    for theme in discover_themes(verified_reviews):
        keywords = [k.lower() for k in theme.get("keywords", [])]
        matched = [r for r in verified_reviews if any(kw in r["text"].lower() for kw in keywords)]
        if matched:
            themes.append({"name": theme["name"], "count": len(matched), "samples": [r["text"] for r in matched[:3]]})
    return themes
