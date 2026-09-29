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

## App API (for the frontend)

This project is becoming a mobile app, targeting **Android and iOS** — a friend owns the
frontend, we own the backend. The frontend is not our job; this section is the contract
so it can be built against without needing to read our code.

- `backend/api.py`: FastAPI wrapper around `run_week()`. Runs on port 8000
  (`uvicorn api:app --host 0.0.0.0 --port 8000`, or via `docker compose up`).
- `GET /health` — `{"status": "ok"}`. Liveness check.
- `POST /weeks/{week_number}/run` — runs the full pipeline for that week (gather → check →
  score → analyze → store) and returns the dashboard payload:
  `{"week": int, "rejected_count": int, "rejected_by_reason": {reason: count}, "themes": [{"name", "count", "samples": [str], "score": -5..5, "reasoning": str, "next_step": str}]}`.
  404 if no data exists for that week number.
- CORS is currently open (`allow_origins=["*"]`) to unblock local frontend dev — tighten
  to the real frontend origin before the demo/submission.
- Verified locally: `GET /health` → 200, `POST /weeks/1/run` → full themed, scored result
  with clean UTF-8 (no encoding issues — double-checked raw response bytes after an initial
  false alarm from a Windows terminal display artifact, not a real bug).
- Not yet re-verified in Docker after this change (daemon wasn't running) — the Dockerfile
  now runs `uvicorn` instead of the old test script; `docker-compose.yml` exposes port 8000.

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
- [x] Real Gatherer pulled in from `sarthak` branch (`backend/gatherer/`) — see below
- [x] `run_week()` wired to the real Gatherer (gather is real; score is still our stub
      pending the real Scorer)
- [x] Critical Checker bug found + fixed against real data (see below)
- [x] Cross-batch Hindsight learning proven against real data (see below)
- [x] Real Scorer built (`backend/scorer.py`) — LLM-based theme discovery, no
      separate Scorer teammate branch exists yet (see below)
- [x] Production Hindsight bank contamination found + fixed (see below)
- [ ] Dashboard hookup

## Gatherer (data) — `backend/gatherer/`
Two branches per the flow diagram: `own` (real feedback about the business) and
`market` (feedback on similar products). Sources: `csv` (Kaggle datasets, columns
auto-detected), `playstore` (live, google-play-scraper), `appstore` (live, Apple RSS).

```bash
cd backend
python -m gatherer inspect ../data/raw/some_kaggle.csv    # profile schema, suggest mapping
python -m gatherer --config gatherer_config.json          # -> data/cleaned/reviews.csv
```
Output columns (Checker input): `id, source, origin, business, date, week, rating, text,
title, author, url`. `rating` is always 1-5 (or empty), `date` is ISO, `week` is ISO week
(`2026-W39`). `id` is a stable hash. For `run_week()`: `gatherer.load(week="2026-W39")`.
Gatherer only drops rows with no text + exact same-id repeats; spam/dupe/gibberish
filtering is left to Checker. Raw Kaggle files go in `data/raw/` (gitignored).

### Current data (`backend/gatherer_config.json`)
- **own = "Telco"**: Kaggle `beatafaron/telco-customer-churn-realistic-customer-feedback`,
  file `telco_churn_with_all_feedback.csv` (7,043 rows; auto-downloaded via kagglehub).
  Feedback text is LLM-generated from each IBM-Telco customer profile — fine for the
  prototype, don't pitch it as real reviews. No rating, no date in the source:
  `rating` is empty, dates are **simulated** (stable per row, spread over 12 weeks ending
  2026-09-27, flagged `date_simulated=True`). Extra columns carried for the Analyst:
  `churn, tenure_months, contract, internet_service, monthly_charges, payment_method`.
- **market**: live Google Play (US) reviews for Verizon, AT&T, Xfinity — 2,000 each,
  covers ~2026-07-10 .. 2026-09-27, real dates and 1-5 ratings.
- Skipped: `telco_prep.csv` (same text lowercased) and `telco_noisy_feedback_prep.csv`
  (75% missing text, half the rest truncated) — the noisy one could be a Checker test set.

## Wiring the real Gatherer into run_week()

`run_week(week_number)` keeps its existing integer interface (so the API contract for the
frontend doesn't change) but now resolves `week_number` to the Nth chronological ISO week
present in `data/cleaned/reviews.csv` (1 = earliest week gathered), loads it via
`gatherer.load()`, and runs the real pipeline on it.

## The real Scorer (`backend/scorer.py`)

No separate Scorer teammate branch exists yet (only `sarthak` for the Gatherer). Since
numeric scoring (-5..+5) is the Analyst's job, not the Scorer's, the Scorer's actual
remaining job is just theme discovery — group reviews, count mentions, keep samples. We
built this ourselves rather than keep hand-writing keyword lists per dataset:
- `discover_themes()` samples up to 60 reviews and asks Groq to identify up to 5 recurring
  themes with a name + matching keywords.
- `score_themes()` uses those LLM-discovered keywords to locally match *all* verified
  reviews to a theme (cheap — no LLM call per review) and returns
  `[{"name", "count", "samples"}, ...]`.
- This replaces the earlier hardcoded `THEME_KEYWORDS` dict (written for imaginary mock
  data — "login issues", "dark mode" — which don't match real Telco feedback at all) with
  something that generalizes to any dataset.
- Verified against real week-1 data: discovered `payment preferences`, `pricing
  perception`, `service quality`, `contract flexibility`, `churn and switching` — all
  genuinely relevant Telco/ISP themes, none hardcoded.

## Production Hindsight bank contamination (found + fixed)

Running the real pipeline end-to-end surfaced a second instance of the contamination bug
from the batch-learning demo — but this time in **production**, not a test script. The
Analyst's reasoning for real week-1 data referenced "login crashes (-5)" and "login
stability" even though no login theme existed anywhere in that week's real data. Cause:
`run_week()` (and therefore the live `POST /weeks/{n}/run` API endpoint the mobile app will
call) used the default Hindsight bank (`feedback-analyser`), which still held every mock
memory written during Phases 2-4 testing (fake "login issues"/"dark mode" data). Fixed by
moving the production `BANK_ID` in `memory.py` to `feedback-analyser-v2` — confirmed clean
by re-running `run_week(1)` twice in a row: the second run's reasoning correctly referenced
*only* real numbers from the first run's genuine stored result (e.g. "403 overall,
consistently the top complaint for multiple weeks"), no phantom login references.
**`feedback-analyser` (no suffix) is permanently stale — never repoint production at it.**

## Critical Checker bug found on real data (fixed)

Running the Checker on the first 300 real reviews rejected **all 300** as "gibberish" —
obviously wrong for genuine, well-formed customer feedback. Root cause: the gibberish
rule's "4+ consecutive consonants in a word" check flagged the ordinary word **"months"**
(m‑o‑n‑t‑h‑s has 4 consonants in a row after the o), and "months" appears constantly in
real reviews ("customer for 22 months"). That rule was removed from `checker.py` —
the vowel-ratio check alone already correctly catches genuine gibberish (verified against
the original mock dataset, same 6/12 result as before) without this false-positive risk.
**Lesson: our mock dataset in Phase 1 wasn't adversarial enough to catch this — a rule can
look correct against a small hand-built test set and still break badly at real-data scale.**

## Proof Hindsight is learning across real batches (`backend/demo_hindsight_learning.py`)

To demonstrate — not just claim — that the Analyst's reasoning improves with memory, this
script runs the real gathered data (sorted chronologically, oldest first) in two batches
through a **dedicated demo Hindsight bank**, separate from the production bank in
`memory.py`, so results are never contaminated by earlier mock/test memories.

**Current run (`feedback-analyser-real-demo-v3`, using the real `scorer.py`):**
- **Batch 1** (300 reviews, clean bank): 5 LLM-discovered themes, all positive — *Speed and
  Reliability* +5 (169 mentions), *Pricing and Affordability* +5 (291), *Payment
  Convenience* +5 (273), *Contract Flexibility* +4 (210), *Service Type Preference* +5
  (239). No negative themes yet.
- **Batch 2** (550 reviews, Analyst can now recall batch 1): the Scorer independently
  discovered *differently-worded* theme names this time (e.g. "pricing reasonableness"
  instead of "Pricing and Affordability") — and Hindsight's semantic recall still bridged
  the difference correctly. Reasoning for "pricing reasonableness" states *"Historical data
  shows it has been identified as the product's single biggest strength (291 mentions)"* —
  batch 1's exact figure, despite the theme's name changing. Two new negative themes
  emerged that didn't exist in batch 1: **contract and churn (-3, 340 mentions)** and
  **internet inclusion (-3, 1 mention)** — correctly identified as real, newly-visible
  problems rather than being padded into the existing positive themes.
- This is a stronger result than the earlier stub-scorer run below: it proves recall isn't
  just matching identical strings between weeks, it's genuinely semantic.

**Earlier run (`feedback-analyser-real-demo-v2`, using the old keyword-based stub scorer,
kept for history):** billing & pricing +5→+4 (297→464 mentions, reasoning cited "up from
297"), internet reliability +5 both batches (cited "194 positive mentions" from batch 1), a
new theme **app login issues (-5)** appeared only in batch 2. Superseded by v3 above now
that the real Scorer exists, but was the first working proof of the recall loop.

Note: an earlier-still run (bank `feedback-analyser-real-demo`, no suffix) was contaminated
by the "months" Checker bug above (batch 1 wrongly rejected as 100% gibberish) — disregard
it entirely; only `-v2` and `-v3` are valid.
