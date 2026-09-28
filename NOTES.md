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
