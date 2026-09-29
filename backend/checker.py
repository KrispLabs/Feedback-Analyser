"""Checker: the filter. Marks each cleaned review true (verified) or false
(rejected) using simple rules, and passes only verified reviews onward to the
Scorer. Input schema (from the Gatherer): id, source, date, rating, text."""

import csv
import re
from collections import Counter

MIN_WORDS = 4
VOWEL_RATIO_THRESHOLD = 0.2
REPEATED_WORD_RATIO_THRESHOLD = 0.5
# A word must also appear this often: in a 4-word review any repeat hits the
# ratio alone, rejecting real ones like "Good food, good price."
MIN_REPEATS = 3


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()


def _is_too_short(text: str) -> bool:
    return len(text.split()) < MIN_WORDS


def _is_repeated_phrase(text: str) -> bool:
    words = text.split()
    if not words:
        return True
    most_common_count = Counter(words).most_common(1)[0][1]
    return (most_common_count >= MIN_REPEATS
            and most_common_count / len(words) >= REPEATED_WORD_RATIO_THRESHOLD)


def _is_gibberish(text: str) -> bool:
    """Heuristic, not a dictionary check: flags text with an unusually low
    vowel ratio across the whole review (real English averages ~38-40%
    vowels; random keyboard-mash text like "asdkj aksjd" comes in under 20%).
    A per-word "long consonant run" rule was tried and removed: it flagged
    ordinary words like "months" (m-o-n-t-h-s has 4 consonants in a row) as
    gibberish, incorrectly rejecting every real review that used them.

    Only Latin letters are measured. Counting every alphabetic character put
    Hindi and Telugu reviews at a 0% "aeiou" ratio and rejected all of them --
    for a Hyderabad shop, a big share of its real reviews. Non-Latin text isn't
    judged by this rule at all; romanised Hinglish still is."""
    letters = [c for c in text if "a" <= c <= "z"]
    if len(letters) < 6:
        return False
    vowels = sum(1 for c in letters if c in "aeiou")
    return (vowels / len(letters)) < VOWEL_RATIO_THRESHOLD


def check_reviews(reviews: list[dict]) -> tuple[list[dict], int, dict]:
    """Returns (verified_reviews, rejected_count, rejected_by_reason)."""
    seen_normalized = set()
    verified = []
    rejected_by_reason = Counter()

    for review in reviews:
        text = review["text"]
        normalized = _normalize(text)

        if normalized in seen_normalized:
            rejected_by_reason["duplicate"] += 1
            continue
        if _is_too_short(normalized):
            rejected_by_reason["too_short"] += 1
            continue
        if _is_repeated_phrase(normalized):
            rejected_by_reason["repeated_phrase"] += 1
            continue
        if _is_gibberish(normalized):
            rejected_by_reason["gibberish"] += 1
            continue

        seen_normalized.add(normalized)
        verified.append(review)

    rejected_count = sum(rejected_by_reason.values())
    return verified, rejected_count, dict(rejected_by_reason)


def load_reviews_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    reviews = load_reviews_csv("data/week_1_mock.csv")
    verified, rejected_count, breakdown = check_reviews(reviews)

    print(f"Input reviews: {len(reviews)}")
    print(f"Verified: {len(verified)}")
    print(f"Rejected: {rejected_count} {breakdown}")
    print("\nVerified reviews:")
    for r in verified:
        print(f"- [{r['id']}] {r['text']}")
