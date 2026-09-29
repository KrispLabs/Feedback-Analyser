"""Analyst: explains why each theme's score is what it is and what to do
next, using this run's scored themes plus Hindsight's memory of past runs.

The business is whatever the Gatherer pulled feedback for -- a mobile app, a
telecom provider, a cafe. The prompt used to say "app feedback themes", and it
showed: analysing Cafe Niloufer produced advice about "the app" and "UI design"
for a tea shop. It is written neutrally now, and the caller passes the business
name and the period the data covers so the model stops assuming "this week".

Score scale: -5 to +5, like a business owner triaging feedback.
  +5 = the single thing we're best at right now (keep doing it).
  -5 = the single most urgent problem, work on this instantly.
  Everything else is ranked the same way on each side of zero: positives are
  strengths worth protecting (closer to +5 = more important), negatives are
  problems worth fixing (closer to -5 = more urgent)."""

import json

from llm import call_llm, strip_code_fences
from memory import HindsightMemory

SYSTEM_PROMPT = """You are an Analyst that scores customer-feedback themes on a \
scale from -5 to +5, the way a small business owner would triage feedback.

Think of it like running a bakery:
- "customers love the sourdough" -> +5 (the single biggest strength, keep doing exactly this)
- "friendly staff" -> +3 (a real strength, but not as decisive as the +5)
- "seating is a bit cramped on weekends" -> -2 (a real complaint, but low priority)
- "health inspector found mold in the display case" -> -5 (fix this before anything else, instantly)

Apply the same logic to whatever business you are given. It may be a cafe, a shop, a
telecom provider or a mobile app — you are told which. Write about THAT business and
the things its customers actually mention. Never assume it is an app: do not refer to
"the app", "users", "releases" or "UI" unless the reviews themselves do.

- +5: the single thing the business is best at right now.
- +1 to +4: other genuine strengths, ranked by importance (closer to +5 = more important to protect).
- -1 to -4: real problems, ranked by urgency (closer to -5 = fix sooner).
- -5: the single most urgent problem — the owner must work on this instantly, before anything else.

Describe the data using the period you are given, not "this week" unless that is the
period. For the theme you are given, respond with ONLY a JSON object:
{"score": <int -5..5>, "reasoning": "<why this score, referencing the review data and any past-run trend you were given, e.g. 'this has been the top complaint for 3 runs straight'>", "next_step": "<if score is negative: a concrete, prioritized action the owner can take; if positive: what to keep doing/protect>"}"""

FALLBACK = json.dumps(
    {
        "score": 0,
        "reasoning": "LLM unavailable, defaulted to neutral.",
        "next_step": "Retry analysis once Groq is reachable.",
    }
)


def analyze_theme(theme: dict, memory: HindsightMemory, business: str = "",
                  period: str = "this week", before_week: int | None = None) -> dict:
    past_context = memory.recall_context(f"past feedback about {theme['name']}",
                                         before_week=before_week)
    context_block = "\n".join(f"- {c}" for c in past_context) or "No past runs recorded yet."

    samples = "\n".join(f"- {s}" for s in theme.get("samples", []))
    user_prompt = (
        (f"Business: {business}\n" if business else "")
        + f"Period covered: {period}\n"
        f"Theme: {theme['name']}\n"
        f"Mentions in this period: {theme.get('count')}\n"
        f"Sample reviews:\n{samples}\n\n"
        f"Relevant memory from past runs:\n{context_block}"
    )

    raw = call_llm(SYSTEM_PROMPT, user_prompt, fallback=FALLBACK)
    result = {**json.loads(FALLBACK), "degraded": True} if raw == FALLBACK else _parse(raw)
    return {**theme, **result}


def _parse(raw: str) -> dict:
    """Coerce the model's reply into {score: int -5..5, reasoning, next_step,
    degraded}. Callers format score with :+d and sort on it, so a "-3" string,
    a 2.5, or a missing key used to crash the run after every paid API call had
    already been made. A reply we can't use is marked degraded rather than
    passed off as a real neutral 0."""
    try:
        result = json.loads(strip_code_fences(raw))
        if not isinstance(result, dict):
            raise TypeError(f"expected a JSON object, got {type(result).__name__}")
        score = max(-5, min(5, round(float(result["score"]))))
        return {"score": score,
                "reasoning": str(result.get("reasoning", "")),
                "next_step": str(result.get("next_step", "")),
                "degraded": False}
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return {"score": 0,
                "reasoning": f"Could not parse the model's reply: {raw[:300]}",
                "next_step": "Could not parse structured output; review manually.",
                "degraded": True}


def analyze_week(themes: list[dict], memory: HindsightMemory, business: str = "",
                 period: str = "this week", before_week: int | None = None) -> list[dict]:
    """business/period default to run_week()'s weekly framing, so its existing
    call site is unchanged; analyse_shop.py passes a shop name and date span.
    before_week: only recall weeks earlier than this (see recall_context)."""
    return [analyze_theme(theme, memory, business, period, before_week) for theme in themes]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mock_themes = [
        {
            "name": "login issues",
            "count": 12,
            "samples": [
                "App keeps crashing when I try to log in every single time",
                "Login fails with an error every time I enter the right password",
            ],
        },
        {
            "name": "dark mode",
            "count": 5,
            "samples": ["Really happy with the new dark mode update looks great"],
        },
    ]

    with HindsightMemory("Analyst Selftest App", bank_id="feedback-analyser-selftest") as memory:
        analyzed = analyze_week(mock_themes, memory)
        for theme in analyzed:
            print(f"\n{theme['name']} -> score {theme['score']}")
            print(f"  reasoning: {theme['reasoning']}")
            print(f"  next_step: {theme['next_step']}")
