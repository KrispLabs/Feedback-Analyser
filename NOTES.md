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
- Input to Analyst: Scorer's themes format (name, count, sample reviews) — TBD, confirm
  format with Scorer owner. The Analyst assigns the score itself (see below), so the
  Scorer does not need to pre-compute sentiment/severity.
- Hindsight schema (ours to define): per-week record of themes, scores, next-steps, keyed
  so future weeks can recall prior weeks.

### Scoring scale (-5 to +5)
Decided so Groq tells the user specifically where they're lagging, not just a generic
sentiment. Framed like a business owner triaging feedback (bakery analogy used to anchor
the model's calibration in the prompt):
- **+5** — the single thing the product is best at right now (keep doing it).
- **+1 to +4** — other genuine strengths, ranked by importance (closer to +5 = protect this more).
- **-1 to -4** — real problems, ranked by urgency (closer to -5 = fix sooner).
- **-5** — the single most urgent problem; work on this instantly, before anything else.
The Analyst (Groq) assigns this score per theme, with reasoning that references both this
week's data and any recalled trend from past weeks.

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
  `{"rejected_count": int, "themes": [{"name", "count", "score", "reasoning", "next_step", "samples": [str, ...]}]}`
  (`score` updated in Phase 3 to the -5..+5 scale below; superseded the earlier sentiment/severity fields.)
- Verified: stored a week-1 login-issues theme and recalled it back correctly.

**Phase 3 — Analyst** (`backend/llm.py` + `backend/analyst.py`)
- `llm.py`: shared Groq call helper (`call_llm`), 3 retries with backoff, safe JSON
  fallback if Groq fails. Model: `openai/gpt-oss-120b` — Groq's available model lineup
  changed since training data cutoff, confirmed live via `client.models.list()`.
  Placeholder until reconciled with the Scorer's own shared `llm.py` (per the brief, the
  Scorer owns this file; ours exists so Analyst isn't blocked).
- `analyst.py`: `analyze_theme()` recalls past-week context from Hindsight for that theme,
  then prompts Groq (system prompt anchors the -5..+5 scale with the bakery analogy) to
  return `{"score", "reasoning", "next_step"}` per theme.
- Verified end-to-end against real Groq + Hindsight: "login issues" (12 mentions, recalled
  trend from a prior test week) scored **-5** with reasoning explicitly citing the
  recurring trend, and a concrete immediate action as next_step. "dark mode" (5 positive
  mentions, no history) scored **+3** — correctly a real strength but not maxed since
  it's not the single standout, next_step was "keep doing this."
- Fixed along the way: a `UnicodeEncodeError` printing Groq's output on Windows console
  (cp1252 can't encode some Unicode punctuation Groq returns) — `sys.stdout.reconfigure(encoding="utf-8")`
  at the entrypoint. Worth remembering for any other script that prints LLM output on Windows.
- Needs the Scorer's real themes format confirmed before final integration (currently
  stubbed as `{"name", "count", "samples"}`).

**Phase 4 — `run_week()` orchestrator** (`backend/run_week.py`)
- Wires `stub_gather_week` → `check_reviews` → `stub_score_themes` → `analyze_week` →
  `HindsightMemory.store_week`, returns one dict for the dashboard.
- `stub_gather_week`/`stub_score_themes` are placeholders for the Gatherer/Scorer's real
  modules (naive keyword-matching for theme grouping) — swapping in the real
  implementations later is a one-line change since the interfaces are already agreed.
- Verified end-to-end on `week_1_mock.csv`: 6/12 rejected (matches Phase 1 test), 3 themes
  found and scored with sensible relative prioritization — **login issues: -5** (most
  urgent, 3 mentions), **loading speed: -3** (real problem, less urgent than login),
  **dark mode: +2** (mild strength, only 1 mention). Result was also stored back into
  Hindsight for next week's recall.

**Next up (not started)** — swap stubs for the real Gatherer/Scorer modules once
teammates push them; end-to-end test across all 4 demo weeks; dashboard hookup.

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
- [x] Docker build + run verified end-to-end (see Docker section above)
- [x] Flow diagram received (Feedback Synthesiser: Gatherer -> Reasoning [Checker + Scorer]
      -> Analyst -> Output/Presentation, with Analyst feeding back into Output)
- [x] Phase 1 — Checker (`backend/checker.py`)
- [x] Phase 2 — Hindsight memory layer (`backend/memory.py`)
- [x] Phase 3 — Analyst + shared Groq helper (`backend/llm.py`, `backend/analyst.py`)
- [x] Phase 4 — `run_week()` orchestrator (`backend/run_week.py`), verified end-to-end
- [ ] Swap stubbed Gatherer/Scorer for teammates' real modules once pushed
- [ ] Dashboard hookup
