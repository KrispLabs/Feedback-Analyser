"""Shared Groq call helper: one function for all AI calls, with retries and a
safe fallback when the model fails. Used by the Analyst and the Scorer.

openai/gpt-oss-120b is a reasoning model: by default it spends completion
tokens on hidden chain-of-thought before writing an answer. With no cap, a
long-enough prompt makes it burn the entire completion budget on reasoning
and return empty content (finish_reason="length", reasoning_tokens roughly
equal to completion_tokens) -- discovered when the Scorer's theme-discovery
call returned "" for real data. reasoning_effort="low" plus an explicit
max_tokens fixes it and also matters for cost: our Groq plan caps at 8,000
tokens PER MINUTE, shared across every call in one run_week() execution, so
low reasoning effort keeps each call's token usage well within budget.

Groq also enforces a separate, much bigger cap: 200,000 tokens PER DAY. Once
that's exhausted, a 429's Retry-After can be tens of minutes (the time until
midnight UTC-ish reset), not seconds -- discovered when a routine test
appeared to hang for 4+ minutes. Blindly sleeping for whatever Retry-After
says (the original fix here) is correct for the per-minute limit but a bad
idea for the daily one: nothing recovers by waiting 25 minutes inside a
single function call. See MAX_RATE_LIMIT_WAIT below."""

import re
import time

from groq import Groq, RateLimitError

from config import load_keys

MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 1500
RATE_LIMIT_FALLBACK_WAIT = 20  # seconds, used when Groq doesn't send Retry-After
MAX_RATE_LIMIT_WAIT = 30  # never sleep longer than this even if Retry-After asks for more


def call_llm(system_prompt: str, user_prompt: str, max_retries: int = 3, fallback: str | None = None) -> str:
    """A single run_week() can make several sequential calls (one Scorer call
    + one Analyst call per theme) against a Groq plan capped at 8,000 tokens
    PER MINUTE -- so a 429 here is an expected, recoverable condition, not a
    rare edge case. The generic exponential backoff below (max ~7s across 3
    attempts) isn't enough to outlast a per-minute window resetting, so a
    RateLimitError gets its own longer wait, honoring the server's
    Retry-After header -- but capped at MAX_RATE_LIMIT_WAIT: if Groq asks for
    longer than that, retrying won't help within this call (daily quota, not
    a per-minute window), so fail fast to the fallback instead of hanging."""
    client = Groq(api_key=load_keys()["GROQ_API_KEY"])
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                reasoning_effort="low",
                max_tokens=MAX_TOKENS,
            )
            choice = response.choices[0]
            # the reasoning model can burn its whole budget and return ""/None
            # with a normal 200 -- that is a failed call, not an answer
            if not (choice.message.content or "").strip():
                raise ValueError(f"empty completion (finish_reason={choice.finish_reason!r})")
            return choice.message.content
        except RateLimitError as e:
            last_error = e
            try:  # seconds normally, but HTTP also allows a date here
                wait = float(e.response.headers.get("retry-after") or RATE_LIMIT_FALLBACK_WAIT)
            except ValueError:
                wait = RATE_LIMIT_FALLBACK_WAIT
            if wait > MAX_RATE_LIMIT_WAIT:
                break  # daily-quota-scale wait -- retrying here is futile, fail fast
            if attempt < max_retries - 1:
                time.sleep(wait)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    if fallback is not None:
        return fallback
    raise RuntimeError(f"Groq call failed after {max_retries} attempts: {last_error}")


def strip_code_fences(text: str) -> str:
    """The model sometimes wraps JSON in ```json ... ``` despite being told not
    to; json.loads() rejects that, so unwrap it before parsing."""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return match.group(1).strip() if match else text.strip()
