"""Analyst: explains why each theme's score is what it is and what to do
next, using this week's scored themes plus Hindsight's memory of past weeks.

Score scale: -5 to +5, like a business owner triaging feedback.
  +5 = the single thing we're best at right now (keep doing it).
  -5 = the single most urgent problem, work on this instantly.
  Everything else is ranked the same way on each side of zero: positives are
  strengths worth protecting (closer to +5 = more important), negatives are
  problems worth fixing (closer to -5 = more urgent)."""

import json

from llm import call_llm
from memory import HindsightMemory

SYSTEM_PROMPT = """You are an Analyst that scores product feedback themes on a \
scale from -5 to +5, the way a small business owner would triage feedback.

Think of it like running a bakery:
- "customers love the sourdough" -> +5 (the single biggest strength, keep doing exactly this)
- "friendly staff" -> +3 (a real strength, but not as decisive as the +5)
- "seating is a bit cramped on weekends" -> -2 (a real complaint, but low priority)
- "health inspector found mold in the display case" -> -5 (fix this before anything else, instantly)

Apply the same logic to app feedback themes:
- +5: the single theme the product is best at right now.
- +1 to +4: other genuine strengths, ranked by importance (closer to +5 = more important to protect).
- -1 to -4: real problems, ranked by urgency (closer to -5 = fix sooner).
- -5: the single most urgent problem — the user must work on this instantly, before anything else.

For the theme you are given, respond with ONLY a JSON object:
{"score": <int -5..5>, "reasoning": "<why this score, referencing the review data and any past-week trend you were given, e.g. 'this has been the top complaint for 3 weeks straight'>", "next_step": "<if score is negative: a concrete, prioritized action; if positive: what to keep doing/protect>"}"""

FALLBACK = json.dumps(
    {
        "score": 0,
        "reasoning": "LLM unavailable, defaulted to neutral.",
        "next_step": "Retry analysis once Groq is reachable.",
    }
)


def analyze_theme(theme: dict, memory: HindsightMemory) -> dict:
    past_context = memory.recall_context(f"past weeks feedback about {theme['name']}")
    context_block = "\n".join(f"- {c}" for c in past_context) or "No past weeks recorded yet."

    samples = "\n".join(f"- {s}" for s in theme.get("samples", []))
    user_prompt = (
        f"Theme: {theme['name']}\n"
        f"Mentions this week: {theme.get('count')}\n"
        f"Sample reviews:\n{samples}\n\n"
        f"Relevant memory from past weeks:\n{context_block}"
    )

    raw = call_llm(SYSTEM_PROMPT, user_prompt, fallback=FALLBACK)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"score": 0, "reasoning": raw, "next_step": "Could not parse structured output; review manually."}

    return {**theme, **result}


def analyze_week(themes: list[dict], memory: HindsightMemory) -> list[dict]:
    return [analyze_theme(theme, memory) for theme in themes]


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

    with HindsightMemory() as memory:
        analyzed = analyze_week(mock_themes, memory)
        for theme in analyzed:
            print(f"\n{theme['name']} -> score {theme['score']}")
            print(f"  reasoning: {theme['reasoning']}")
            print(f"  next_step: {theme['next_step']}")
