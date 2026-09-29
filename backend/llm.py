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
low reasoning effort keeps each call's token usage well within budget."""

import time

from groq import Groq

from config import load_keys

MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 1500


def call_llm(system_prompt: str, user_prompt: str, max_retries: int = 3, fallback: str | None = None) -> str:
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
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    if fallback is not None:
        return fallback
    raise RuntimeError(f"Groq call failed after {max_retries} attempts: {last_error}")
