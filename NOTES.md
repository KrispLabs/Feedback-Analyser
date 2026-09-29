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

## Backend phases (this repo, our 3 roles)

Pushed to `Chaitanya` in pairs of phases to minimise integration errors.

**Phase 1 — Checker** (`backend/checker.py`)
- Rule-based true/false verification: duplicate (normalized-text hash), too-short
  (<4 words), repeated-phrase spam (one word ≥50% of the review), gibberish (low
  vowel ratio or a 4+ consonant run in a word — intentionally simple, can misfire on
  dense real words like "strength").
- `check_reviews(reviews) -> (verified, rejected_count, rejected_by_reason)`.
- Tested against `backend/data/week_1_mock.csv` (a hand-built mock dataset with
  planted duplicates/spam/gibberish, since the Gatherer's real cleaned CSV isn't
  ready yet) — all 4 rules fire correctly, 6/12 reviews verified.

**Phase 2 — Hindsight memory layer** (`backend/memory.py`)
- `HindsightMemory` class, used as a context manager (`with HindsightMemory() as m:`)
  so the aiohttp session closes cleanly — fixes the "unclosed client session"
  warning from last night's raw test script.
- `store_week(week_number, week_result)`: retains one memory per week, tagged
  `week:<n>`, containing rejected_count + themes (JSON).
- `recall_context(query)`: semantic recall across past weeks for the Analyst to
  reason about trends.
- Weekly record schema (ours, shared with Scorer/Analyst):
  `{"rejected_count": int, "themes": [{"name", "count", "sentiment", "severity", "samples": [str, ...]}]}`
- Verified: stored a week-1 login-issues theme and recalled it back correctly.

**Phase 3 — Analyst** (next) — `llm.py` (Groq call helper, retry+fallback — placeholder
until reconciled with the Scorer's shared `llm.py`) + `analyst.py` (this week's themes +
recalled past weeks → reasoning + next steps per theme). Needs the Scorer's real themes
format confirmed before final integration.

**Phase 4 — next** — `run_week()` orchestrator wiring gather → check → score → analyze →
store. Needs real Gatherer/Scorer module signatures; stubbed until then.

## Keys / secrets
- Stored in `keys.csv` (gitignored) — Groq (LLM) and Hindsight Cloud API keys.
- Never commit `keys.csv`.
- For Docker: copy `.env.example` to `.env` in the project root and fill in real values.
  `.env` is gitignored too. `backend/config.py` reads real environment variables first
  (how Docker/`.env` inject them) and falls back to `keys.csv` for local non-Docker dev.

## Docker
- `backend/Dockerfile` (python:3.12-slim, installs `requirements.txt`) +
  root `docker-compose.yml` so teammates can run the backend without installing
  Python/pip locally.
- Verified end-to-end on 2026-09-28:
  - `docker compose build` — image builds cleanly, all deps (`hindsight-client`, `groq`)
    resolve and install with no conflicts.
  - `docker compose run --rm backend` with no `.env` present — container still starts
    (env file is marked `required: false` in `docker-compose.yml`) and the app itself
    raises a clear `Missing API key(s): GROQ_API_KEY, HINDSIGHT_API_KEY` error instead of
    Docker failing to start. Fixed after first attempt showed Compose hard-erroring when
    `.env` didn't exist yet.
  - `docker compose run --rm backend` with real keys passed as ephemeral `-e` env vars
    (not written to disk) — full `hindsight_test.py` round trip succeeded inside the
    container: retained a test memory and recalled it back correctly.
  - Known cosmetic issue, not blocking: an "Unclosed client session" aiohttp warning
    prints on exit — cleanup for the real client wrapper, not a correctness problem.

## Status
- [x] Folder scaffolded
- [x] Hindsight store/recall test memory working — see `backend/hindsight_test.py`
      (retain + recall round trip confirmed against real Hindsight Cloud API)
- [x] Docker build + run verified end-to-end (see Docker section above)
- [ ] Flow diagram received from user (pending — will drop in `flow.png` or similar)
- [ ] Full backend coding starts tomorrow (need to close aiohttp session cleanly in
      the real client wrapper — currently prints an "unclosed client session" warning)
