"""Shared Groq call helper: one function for all AI calls, with retries and a
safe fallback when the model fails. Used by the Analyst (and, once merged with
the Scorer's own llm.py, by theme grouping too)."""

import time

from groq import Groq

from config import load_keys

MODEL = "openai/gpt-oss-120b"


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
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    if fallback is not None:
        return fallback
    raise RuntimeError(f"Groq call failed after {max_retries} attempts: {last_error}")
