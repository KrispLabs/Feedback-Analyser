# Feedback Analyser — Team Plan (Microsoft Hackathon)

## Our scope: Lead + Analyst + Checker

We're covering 3 of the 4 roles. The Scorer role (llm.py, theme grouping) is owned by
another teammate — our Hindsight/analyst code will consume their output format, and our
checker.py output feeds their Scorer.

### Lead + Analyst (the brain)
- Hindsight Cloud integration: store each week's themes/scores/next-steps, recall past
  weeks when a new week comes in.
- Analyst logic: given this week's scored themes + past memory, explain *why* each score
  is what it is and *what to do next* (e.g. "Login complaints rose for 3 weeks straight;
  fix before next release").
- `run_week()`: single entrypoint running the full pipeline in order —
  gather → check → score → analyze → store — returns results for the dashboard.
- Tonight's target: Hindsight storing + recalling a test memory.

### Checker (the filter)
- `checker.py`: marks each review true/false using rules — duplicates, very short text,
  repeated phrases, gibberish.
- Counts rejected reviews for the dashboard.
- Passes only verified reviews downstream to the Scorer.
- Tonight's target: `checker.py` working on the cleaned data (depends on Gatherer's
  cleaned dataset).

### Interfaces we depend on / must define
- Input to Checker: cleaned review rows — id, source, date, rating, text (from Gatherer).
- Output of Checker → Scorer: verified reviews only, plus a rejected count.
- Input to Analyst: Scorer's themes format (reviews mentioning, sentiment, sample reviews) — TBD, confirm format with Scorer owner.
- Hindsight schema (ours to define): per-week record of themes, scores, next-steps, keyed
  so future weeks can recall prior weeks.

## Keys / secrets
- Stored in `keys.csv` (gitignored) — Groq (LLM) and Hindsight Cloud API keys.
- Never commit `keys.csv`.

## Status
- [x] Folder scaffolded
- [x] Hindsight store/recall test memory working — see `backend/hindsight_test.py`
      (retain + recall round trip confirmed against real Hindsight Cloud API)
- [ ] Flow diagram received from user (pending — will drop in `flow.png` or similar)
- [ ] Full backend coding starts tomorrow (need to close aiohttp session cleanly in
      the real client wrapper — currently prints an "unclosed client session" warning)
