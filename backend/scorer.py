"""Scorer: groups verified reviews into themes.

Karthik's implementation (Karthik branch), with fixes applied on top of his
logic for real-data integration -- see NOTES.md for the full story:
  1. `from backend.llm import call_llm` -> `from llm import call_llm` (our
     backend/ package runs flat, not as `backend.*`).
  2. `call_llm(prompt)` -> `call_llm(SYSTEM_PROMPT, prompt, ...)`: our
     call_llm requires a system prompt and a user prompt, not one string.
  3. Sends every verified review in one prompt with no sampling. Tested
     against real week-1 data (604 reviews, ~52,000 tokens) and got a hard
     Groq 413: our plan's rate limit is 8,000 tokens PER MINUTE, shared with
     the Analyst's own calls in the same run -- so this silently returned []
     for any real week (call_llm's fallback swallows the error). Fixed by
     sampling the input down to a token budget that leaves headroom for the
     Analyst's calls in the same run_week() execution.
     Tradeoff: "count" is now based on the sample, not an exact count across
     every verified review that week -- acceptable for relative theme
     importance, but not a precise total. Flagged here rather than silently
     shipped, in case real usage numbers matter later.
  4. Also found (separately, same real-data run): the model occasionally
     writes a count as a word instead of a digit (e.g. `"count": seventy`),
     which breaks json.loads() -- and that happened *after* call_llm already
     succeeded, so call_llm's own retries never saw it and this function
     just returned [] with no visibility into why. Tightened the prompt's
     wording and added a retry around the parse step (not just the API call)
     so one malformed response doesn't waste the whole extraction.

Numeric scoring (-5..+5) is the Analyst's job (see analyst.py), using
Hindsight-informed reasoning -- this module only needs to return
[{"name", "count", "samples"}, ...] per the agreed interface (NOTES.md)."""

import json
import random

from llm import call_llm, strip_code_fences

SYSTEM_PROMPT = "You analyze customer feedback and group it into recurring themes."

SAMPLE_SIZE = 50
MAX_CHARS_PER_REVIEW = 150
PARSE_RETRIES = 2


def extract_themes(verified_reviews, rejected_count=0):
    """
    Processes verified reviews to group them into recurring themes.
    Matches the Scorer interface contract for the Feedback Synthesiser pipeline.
    """
    if not verified_reviews:
        return []

    sample = random.sample(verified_reviews, min(SAMPLE_SIZE, len(verified_reviews)))
    # Extract text from the cleaned review rows
    reviews_text = [review["text"][:MAX_CHARS_PER_REVIEW] for review in sample
                    if isinstance(review.get("text"), str)]

    prompt = f"""
    Analyze the following list of customer reviews and group them into distinct themes.
    You must return a valid JSON array of objects. Do not include markdown formatting.

    Each object must strictly follow this schema:
    - "name": A concise, descriptive string naming the theme.
    - "count": An integer representing the number of reviews that fall under this theme, written as a plain digit such as 12 -- never spelled out as a word.
    - "samples": An array containing 1 to 3 direct string quotes from the reviews that illustrate this theme.

    Reviews to analyze:
    {json.dumps(reviews_text)}
    """

    for attempt in range(PARSE_RETRIES):
        # call_llm natively handles its own 3 retries, backoff, and safe JSON fallback
        response = call_llm(SYSTEM_PROMPT, prompt, fallback="[]")

        try:
            themes = json.loads(strip_code_fences(response))
        except json.JSONDecodeError:
            continue  # malformed output (e.g. a spelled-out count) -- retry once

        # {"themes": [...]}: iterating the dict itself walked its keys and
        # silently returned []
        if isinstance(themes, dict):
            themes = next((v for v in themes.values() if isinstance(v, list)), [])
        if not isinstance(themes, list):
            continue

        # Enforce the agreed data contract before passing to the Analyst. One
        # bad theme is skipped on its own rather than discarding every theme.
        validated_themes = []
        for theme in themes:
            try:
                samples = theme["samples"]
                validated_themes.append({
                    "name": str(theme["name"]),
                    "count": int(theme["count"]),
                    "samples": [samples] if isinstance(samples, str) else list(samples),
                })
            except (KeyError, TypeError, ValueError):
                continue

        # themes but none usable is a malformed reply worth one retry; an
        # empty list (including call_llm's "[]" fallback) is returned as-is
        if validated_themes or not themes:
            return validated_themes

    # Fallback to an empty list to prevent pipeline crashes if the LLM output stays malformed
    return []
