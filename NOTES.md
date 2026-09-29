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

This project is becoming a **webapp** (corrected — earlier noted as Android/iOS, that was
wrong) — a friend owns the frontend, we own the backend. The frontend is not our job; this
section is the contract so it can be built against without needing to read our code.

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
- [x] Real Scorer built by us (`backend/scorer.py`) — LLM-based theme discovery,
      before a separate Scorer teammate branch existed
- [x] Production Hindsight bank contamination found + fixed (see below)
- [x] Karthik's real Scorer pulled in from the `Karthik` branch, replacing our own —
      found and fixed 5 real integration bugs against real data (see below)
- [x] Shop Gatherer — reviews from a shop name + location (see below)
- [x] End-to-end shop CLI (`analyse_shop.py`) verified on Cafe Niloufer, Hitech City
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

## Shop Gatherer — reviews from a shop name + location (`backend/gatherer/sources/shop.py`)

The Gatherer could only reach apps (Play Store / App Store) and offline CSVs. This adds
physical shops: give it a name and a location and it resolves the place, pulls its Google
reviews, and appends them to the same cleaned CSV database everything downstream reads.

```bash
cd backend
python -m gatherer shop "Chai Point" "Banjara Hills, Hyderabad"
python -m gatherer shop "Chai Point" "Hyderabad" --provider serpapi --limit 300
python -m gatherer shop "Third Wave Coffee" "Hyderabad" --origin market   # a competitor
```

Nothing downstream changed — the source yields the same `Review` shape as every other
source, so Checker → Scorer → Analyst → Hindsight → `POST /weeks/{n}/run` all work as-is.

### Two providers (`--provider`)
- **`places`** (default) — Google Places API (New). Official, no scraping, generous free
  tier. **Google only ever returns 5 reviews per place**, so this proves the pipeline but
  is too thin to demo on. Needs `GOOGLE_MAPS_API_KEY`.
- **`serpapi`** — SerpApi's Google Maps scraper, paginated: hundreds of reviews per shop
  with real ratings. 100 free searches/month. Needs `SERPAPI_API_KEY`.

Keys resolve env → `keys.csv` → an `api_key` in the config, so it works the same in Docker
and in local dev. A missing key raises at fetch time naming the exact variable, rather than
at import — the other sources keep working without it.

### Appending, not overwriting
`python -m gatherer shop ...` **adds to** `data/cleaned/reviews.csv` (`--replace` to
overwrite), so you can build a database one shop at a time. Review `id`s are stable hashes,
so re-gathering the same shop updates its rows in place instead of duplicating them —
verified: re-running the same shop twice leaves the row count unchanged.

### Approximate dates
SerpApi returns `iso_date` for most reviews but falls back to `"3 months ago"` phrasing for
some. Those are converted to an approximate ISO date and flagged `date_approx=True` in the
output. Deliberate: `run_week()` buckets by ISO week, and a review dated to roughly the
right fortnight still lands in a week, whereas a review with no date gets an empty `week`
and silently drops out of *every* weekly run.

### Config-file form
Works as a normal source alongside the existing ones, for shops you gather every week:
```json
{"business": "Chai Point",
 "own":    [{"type": "shop", "name": "Chai Point", "location": "Banjara Hills, Hyderabad",
             "provider": "serpapi", "limit": 300}],
 "market": [{"type": "shop", "name": "Third Wave Coffee", "location": "Hyderabad"}]}
```
Ambiguous names (three branches in one city) resolve to Maps' first hit — pass
`place_id` / `--place-id` to pin an exact branch.

### Verified
- All 8 checks in the stubbed end-to-end test pass: relative-date parsing (8 cases), the
  missing-key error, both providers' response shapes, SerpApi pagination across pages,
  `limit` stopping mid-page without wasting an API call, cleaned-CSV output with unique
  16-char ids and a populated `week` on every row, append-dedupe on re-gather, and Checker
  accepting the rows unchanged.
- Both live endpoints reached with a deliberately invalid key: Google returns
  `API_KEY_INVALID` (i.e. the request shape passed field validation), SerpApi returns 401.
  **Not yet run against a real key — no `GOOGLE_MAPS_API_KEY`/`SERPAPI_API_KEY` available
  in this environment.** Add one and the first real pull is the remaining check.
- Gotcha on macOS: a bare venv has no root certificates, so every `urllib` source (this one
  and `appstore.py`) fails with `CERTIFICATE_VERIFY_FAILED`. Fix with
  `pip install certifi && export SSL_CERT_FILE=$(python -c "import certifi;print(certifi.where())")`,
  or run the Docker image, which has system certs.

### `--limit` counts usable reviews, not rows returned (fixed)

First real run against Cafe Niloufer asked for 200 reviews and got 55, having spent
~15 billable SerpApi searches. Not a pagination stall — most Google Maps reviews are
star-only ratings with no text. Those get dropped by `finalise()` and are useless to the
Checker, but `limit` was counting them, so the source paginated to 200 *rows* to reach 55
*usable* ones and billed for the difference.

Fixed three ways:
- Reviews with no text are skipped before they count against `limit`, on both providers.
- Pages 2+ now request `num=20` instead of the default 10. SerpApi rejects `num` on page
  one (`"It always returns 8 results"`), so page one is left alone — same one search,
  twice the reviews after that.
- `max_pages` (default 15) hard-caps billable searches, so a shop whose reviews are almost
  all star-only can't quietly drain a monthly quota. `--max-pages` raises it.

Measured against the live API: **50 usable reviews for 6 billable searches (8.3 per
search), up from 3.7** — 2.2x better. `source.pages_fetched` is reported by
`analyse_shop.py` as the run's cost; it counts pages *requested*, and SerpApi doesn't bill
repeat identical queries, so it reads as an upper bound. SerpApi free tier is 250
searches/month.

## End-to-end shop run — `backend/analyse_shop.py`

One command takes a business name and location all the way to scored, reasoned themes:

```bash
python analyse_shop.py                                  # prompts for both
python analyse_shop.py "Niloufer Cafe" "Hitech City"
python analyse_shop.py "Niloufer Cafe" "Hitech City" --provider serpapi --limit 200
```

Same pipeline as `run_week()` (gather → check → score → analyze → store) but over one
shop's whole review history rather than one ISO week, since a shop you've just looked up
has no prior weeks to slice. `--run N` numbers the run so later runs recall earlier ones.

**Verified end-to-end on real data (Cafe Niloufer, Hitech City — 4.3★, 8,570 reviews):**
55 gathered → 44 verified (11 `too_short`) → 8 themes → all 8 scored by Groq with real
reasoning, no fallbacks. Results were domain-plausible: **tea quality praised +5** and
**tea quality criticized −4** (the chai is both the best thing and the most complained
about), crowded −3, over-priced −3, ambience +3.

Two notes from that run:
- Give each business its own Hindsight bank (`HINDSIGHT_BANK_ID=niloufer-cafe`). The
  production bank holds Telco themes; mixing a cafe into it recreates the contamination
  bug twice-fixed above.
- Give each business its own Hindsight bank (see above).

### Recency window — `--months` (default: last 3 months)

A popular shop has years of reviews; only recent ones say what to fix now. `--months N`
keeps reviews from the last N months (`--months 0` = all time), and because the default
sort is newest-first the shop source **stops paginating once a whole page predates the
cutoff** — the window saves billable searches instead of discarding pages already paid
for. Verified: a 5-page fixture with a 2-page window stops after 3 pages. Early-stop only
applies to `sort=newest`; any other sort filters but walks every page, since rating order
says nothing about dates. Reviews whose only date is relative ("2 weeks ago") are kept and
flagged `date_approx`.

`--since` does the same on the raw gatherer CLI (`python -m gatherer shop ... --since`).

## Analyst prompt made business-generic (`backend/analyst.py`)

The prompt said "Apply the same logic to **app** feedback themes", and against Cafe
Niloufer it showed: the tea shop's advice referenced "the app", "UI design" and "users",
and described 11 months of reviews as "this week". Fixed:
- The scale section now names the business type explicitly and forbids app language
  unless the reviews use it themselves.
- `analyze_theme()` / `analyze_week()` take `business` and `period`, so the model is told
  *"Business: Niloufer Cafe, Hitech City / Period covered: 2026-07-18 to 2026-09-28"*
  instead of inferring a week. Both default to the old weekly framing, so `run_week()`'s
  call site is unchanged.

**Verified on a real re-run** (run 2, 3-month window, 39 verified reviews): a grep for
`the app|UI design|UI/UX|release|sprint|hotfix` across the whole output returned **zero
matches**, where run 1 had several. Themes came back in the shop's own language —
*Excellent Irani Chai and Bun Maska +4*, *Pleasant Ambience +4*, *Crowded Space −4*,
*Expensive Pricing −3*, *Perceived Overhype / Overrated −3*.

**Cross-run Hindsight recall proven on a real business**: run 2's reasoning cites run 1's
actual figures — "flagged in 10 reviews during the first week of September and again in
this period with 5 mentions" (crowding, 10 → 5) and "aligns with prior runs where nine
users flagged pricing" (pricing, 9). The Analyst is genuinely comparing runs, not
restating one batch.

## Wiring the real Gatherer into run_week()

`run_week(week_number)` keeps its existing integer interface (so the API contract for the
frontend doesn't change) but now resolves `week_number` to the Nth chronological ISO week
present in `data/cleaned/reviews.csv` (1 = earliest week gathered), loads it via
`gatherer.load()`, and runs the real pipeline on it.

## Our own placeholder Scorer (superseded by Karthik's real one, kept for history)

No separate Scorer teammate branch existed yet at this point (only `sarthak` for the
Gatherer). Since numeric scoring (-5..+5) is the Analyst's job, not the Scorer's, the
Scorer's actual remaining job is just theme discovery — group reviews, count mentions,
keep samples. We built a placeholder ourselves rather than keep hand-writing keyword lists
per dataset:
- `discover_themes()` sampled up to 60 reviews and asked Groq to identify up to 5 recurring
  themes with a name + matching keywords.
- `score_themes()` used those LLM-discovered keywords to locally match *all* verified
  reviews to a theme (cheap — no LLM call per review) and returned
  `[{"name", "count", "samples"}, ...]`.
- Verified against real week-1 data: discovered `payment preferences`, `pricing
  perception`, `service quality`, `contract flexibility`, `churn and switching` — all
  genuinely relevant Telco/ISP themes, none hardcoded.
- Replaced entirely once Karthik's Scorer landed (below) — the function name
  `score_themes` no longer exists in `backend/scorer.py`.

## Karthik's real Scorer (`backend/scorer.py`, from the `Karthik` branch)

Karthik pushed `scorer.py` — one function, `extract_themes(verified_reviews,
rejected_count)`, sending the whole review list to Groq in one prompt and asking for
`[{"name", "count", "samples"}, ...]` directly, with schema validation on the response.
Good design (matches the interface exactly, defensive validation), but 3 real bugs
surfaced testing it against real data — the same pattern as the Gatherer/Checker
integrations: looks correct on paper, breaks at real scale.

**Bug 1 — wrong import path.** `from backend.llm import call_llm` assumes `backend` is an
importable package from the repo root; our actual layout runs flat from inside `backend/`
(every other module imports `from llm import call_llm`). Fixed by matching our layout.

**Bug 2 — wrong `call_llm` signature.** Karthik called `call_llm(prompt)` with one
argument; our shared `call_llm(system_prompt, user_prompt, ...)` requires two, so this
raised `TypeError` immediately. Fixed by adding a system prompt.

**Bug 3 — sends every review in one prompt, no sampling.** Ran against real week-1 data
(604 reviews) and hit a hard Groq `413`: `Request too large ... tokens per minute (TPM):
Limit 8000, Requested 51985`. Our Groq plan caps at **8,000 tokens per minute, shared
across every call in one `run_week()` run** (the Scorer's discovery call plus one Analyst
call per theme) — any week above roughly a few dozen reviews will always blow this budget,
and `call_llm`'s own fallback swallows the exception into a silent empty result with no
visible error. Fixed by sampling verified reviews down to a token-safe budget (50 reviews,
truncated to 150 chars each) before building the prompt. Tradeoff, documented in
`scorer.py`: `"count"` is now based on the sample, not an exact count across every
verified review that week — fine for relative theme importance, not a precise total.

**Bug 4 (found while fixing #3, but really a shared `llm.py` bug) — reasoning model empty
output.** Even after sampling, `extract_themes` still returned `[]`. Debugging the raw Groq
response showed `finish_reason: "length"` with `reasoning_tokens` almost equal to
`completion_tokens` — `openai/gpt-oss-120b` is a reasoning model that spends completion
tokens on hidden chain-of-thought before writing an answer, and with no cap it burned the
*entire* completion budget on reasoning, leaving zero tokens for the actual JSON. Fixed in
the **shared `llm.py`** (not just `scorer.py`, since the Analyst uses the same model and is
equally exposed, it just hadn't hit a long-enough prompt to trigger it yet): added
`reasoning_effort="low"` and an explicit `max_tokens=1500` to the Groq call.

**Bug 5 (also found during this pass) — model occasionally spells out numbers.** Even with
the above fixed, `extract_themes` was still flaky — some runs returned `[]`. Root cause:
the model sometimes writes `"count": seventy` instead of a digit, which breaks
`json.loads()` *after* `call_llm` already succeeded, so `call_llm`'s own retries never see
it. Fixed by tightening the prompt ("written as a plain digit... never spelled out as a
word") and adding a retry loop around the parse step itself in `scorer.py`, not just around
the API call.

**Verified end-to-end after all 5 fixes:** ran `run_week(1)` on real week-1 data (580
verified reviews) — Karthik's Scorer discovered **10** real themes (overall
satisfaction/loyalty, monthly charges, service reliability, contract preference, churn,
payment methods, customer support, mobile app usability, activation issues, security/phone
plan), and the Analyst scored and reasoned over every one of them correctly, including
citing real cross-week figures ("403 overall", "355 churn reports") with no contamination.
The run took a while (10 sequential Analyst calls, one per theme, all sharing the same
8,000 TPM budget) but completed with real reasoning content throughout — no fallback text
anywhere in the result, so no call actually got stuck in a rate-limit loop this time.

**Follow-up hardening (`backend/llm.py`):** a `run_week()` with more themes than this one
could plausibly hit a real 429 mid-run, and the original backoff (a blind 1s/2s/4s
exponential wait, max ~7s across 3 attempts, same for every error type) is nowhere near
long enough to outlast Groq's per-minute window resetting — it would burn all 3 retries
and fall through to the safe-but-degraded fallback instead of actually recovering. Added a
`RateLimitError`-specific branch that honors the server's `Retry-After` header when present,
falling back to a fixed 20s wait otherwise, while leaving the short exponential backoff in
place for other transient errors (timeouts, 5xx, etc.) where a fast retry is the right call.
`run_week.py` and `demo_hindsight_learning.py` (now on bank `feedback-analyser-real-demo-v4`)
both call `extract_themes` in place of our retired `score_themes`.

## Production Hindsight bank contamination (found + fixed)

Running the real pipeline end-to-end surfaced a second instance of the contamination bug
from the batch-learning demo — but this time in **production**, not a test script. The
Analyst's reasoning for real week-1 data referenced "login crashes (-5)" and "login
stability" even though no login theme existed anywhere in that week's real data. Cause:
`run_week()` (and therefore the live `POST /weeks/{n}/run` API endpoint the webapp will
call) used the default Hindsight bank (`feedback-analyser`), which still held every mock
memory written during Phases 2-4 testing (fake "login issues"/"dark mode" data). Fixed by
moving the production `BANK_ID` in `memory.py` to `feedback-analyser-v2` — confirmed clean
by re-running `run_week(1)` twice in a row: the second run's reasoning correctly referenced
*only* real numbers from the first run's genuine stored result (e.g. "403 overall,
consistently the top complaint for multiple weeks"), no phantom login references.
**`feedback-analyser` (no suffix) is permanently stale — never repoint production at it.**

## Full system verification pass — 2 more bugs found and fixed

Ran every module standalone plus the full pipeline and the API, specifically to answer
"does this actually work" rather than assume it from earlier partial tests.

- **Checker** (`python checker.py`): ✅ correct, 6/12 verified on the mock set, unchanged.
- **Memory** (`python memory.py`): found a real bug — its own `__main__` self-test wrote a
  fake "login issues" memory straight into the **production** bank (`feedback-analyser-v2`)
  every time it ran, silently re-creating the exact contamination problem fixed above.
  Fixed: the self-test now uses a dedicated `feedback-analyser-selftest` bank. Re-verified
  clean afterward.
- **Analyst** (`python analyst.py`): only reads via `recall_context`, never writes, so it
  was never a contamination risk — but running it surfaced two much bigger problems below.
- **Scorer** (Karthik's, on mock data): ✅ correct, 3 coherent themes.
- **`run_week()` end-to-end on real data:** Checker stage still correct (24 rejected), but
  the Scorer's discovery call returned `[]` — see quota exhaustion below.
- **API `GET /health`:** ✅ 200 `{"status": "ok"}`, no Groq dependency, unaffected by
  anything below.

**Bug found — `analyst.py`'s standalone test appeared to hang for 4+ minutes.** Investigated
properly rather than just waiting: the process had near-zero CPU time despite minutes of
wall-clock time (blocked on I/O, not looping), and had live connections to both Groq and
Hindsight. Traced to the actual root cause by reproducing the exact call: **we had
exhausted our Groq plan's 200,000-tokens-PER-DAY quota** (`Used 198530, Requested 5010`)
from this session's extensive testing, and Groq's 429 said "try again in 25m29s". The
rate-limit fix from the previous round was *correctly* honoring that `Retry-After` value —
it just hadn't been tested against the daily cap (only the per-minute one), so a 25-minute
wait inside one function call looked exactly like a hang from the outside.

**Fix:** added `MAX_RATE_LIMIT_WAIT = 30` to `llm.py` — if `Retry-After` asks for longer
than that, retrying inside this call is futile (it's a daily quota, not a per-minute
window), so it now fails fast to the fallback instead of sleeping for however long Groq
asks. Verified: a `call_llm` test that previously would have hung now returns in ~1.5s
even while still rate-limited.

**Observed under quota exhaustion (worth knowing before a live demo):** with almost no
daily quota left, `run_week(1)` completed quickly and did **not** crash or hang — but
`extract_themes` returned `[]` indistinguishable from "genuinely found no themes." A judge
or teammate watching a demo mid-quota-exhaustion would see an empty result with no
indication *why*. Not fixed here (would mean changing Karthik's fallback contract, and we
were nearly out of quota to test a fix against), but flagged: if this matters for the demo,
`extract_themes`/`call_llm` should surface a distinguishable "temporarily unavailable"
state rather than a silently-empty one.

## Shop Gatherer merged from main; SerpApi cost-reporting bug found and fixed

Pulled `main` into `Chaitanya` (fast-forward, no conflicts) — it now includes a whole new
flow built on top of our work: `backend/analyse_shop.py` + `backend/gatherer/sources/shop.py`
resolve a business by name + location, live-scrape its Google Maps reviews via SerpApi (or
Google Places), and run it through the same Checker/Scorer/Analyst/Memory stages. New API
endpoint `POST /shops/analyse`, a thorough `README.md`, and a `HINDSIGHT_BANK_ID` env var in
`memory.py` that generalizes the per-experiment bank pattern we'd been doing manually.
`analyst.py`'s prompt was also generalized to stop assuming "app feedback" now that the
business can be a cafe, shop, or telecom.

**Debugged from the start given a tight SerpApi budget (told: stay under 100 credits,
some already spent).** Zero-cost first: syntax-compiled and imported every backend module
(all clean), unit-tested `shop.py`'s pure logic (`parse_relative_date`, `query`, validation)
with no API calls. Only then one minimal live test — `ShopSource` in isolation (not the
full pipeline, to avoid also spending Groq quota), `max_pages=1`, real business ("Niloufer
Cafe", "Hitech City").

**Bug found: `pages_fetched` undercounts real SerpApi cost by exactly 1 search, every run.**
The live test used 2 actual SerpApi searches (1 to resolve the business to a place, 1 to
fetch the review page), confirmed by request logging, but `source.pages_fetched` reported
only 1 — the initial place-lookup call was never counted. `analyse_shop.py` shows this
number to the user as `cost : N billable SerpApi searches`, so **every run's true cost was
silently underreported by 1 credit** — the kind of bug that quietly erodes trust in a
credit counter someone is watching closely.

Fix required care: `pages_fetched` isn't just a display number, it also gates the
pagination loop (`while ... self.pages_fetched < self.max_pages`). Naively incrementing it
for the lookup too would mean `max_pages=1` fetches **zero** review pages instead of one,
since the lookup would consume the whole budget — a worse bug than the one being fixed.
Solution: split the two concerns. `pages_fetched` stays review-pages-only (preserves the
pagination cap's intended meaning), and a new `searches_used` counts every billable call
(lookup + pages) for accurate cost reporting. `analyse_shop.py` now reports `searches_used`.
Verified with a mocked test (zero API cost): `max_pages=1` still yields exactly 1 review
page, while `searches_used` now correctly reports 2.

**Total SerpApi spend this session: 2 credits** (the one live test above; the mocked
verification cost nothing).

## Second main-branch merge: dashboard frontend, market comparison, hardened pipeline

Pulled `main` into `Chaitanya` again — 5 more commits, 22 files, ~3,400 lines. Fast-forward
wasn't possible this time (real conflicts, both in files this branch had also edited), so
this one needed actual merge judgment rather than just accepting either side.

**What's new:**
- **`frontend/`** — a full dashboard (`app.js`, `index.html`, `styles.css`, ~2,400 lines),
  served by `api.py` at `/` from the same origin as the API (no CORS needed for it).
- **`backend/market.py`** — the "similar market" branch: finds nearby competitors (or uses
  named ones), gathers a small batch of their reviews, and asks Groq once to summarise
  each one's strengths/weaknesses, which the Analyst then scores each theme against.
- **`backend/errors.py`** — typed pipeline exceptions (`NothingToAnalyse` 404,
  `UpstreamError` 502, `ConfigError` 503) instead of overloading `LookupError`/`RuntimeError`,
  which had a real bug: `KeyError` is a `LookupError`, so a plain coding bug (missing dict
  key) was coming back to API clients as a 404 "not found" instead of a 500.
  `api.py` now has global exception handlers so every error returns the same JSON shape.
- **`memory.py` rework** — every memory is now scoped to one business (`business_tag()`),
  fixing a real cross-contamination bug: recalling "Overpriced chai at Niloufer Cafe" used
  to return 26 unrelated Telco memories that the Analyst then cited as the cafe's own past
  trend. Also: Hindsight failures no longer raise — `memory.available`/`memory.error` let
  the analysis continue without past-context rather than losing a run that already paid
  for SerpApi + Groq calls.
- **`checker.py` fix** — `_is_gibberish`/`_normalize` were stripping combining marks and
  measuring vowel ratio over all alphabetic characters, which rejected Hindi/Telugu text
  entirely (0% "aeiou" by construction) — a real problem for a Hyderabad cafe's actual
  reviews. Now Unicode-category-based normalization and Latin-only vowel measurement.
- **`llm.py`** — `call_llm` now also treats an empty completion (reasoning model burns its
  whole budget on hidden reasoning, returns "") as a failure to retry/fall back on, not a
  successful empty answer. Also switched to `get_key()` so a missing `HINDSIGHT_API_KEY`
  no longer breaks every LLM call (it used to, via `load_keys()` demanding every key).
- **HTTPS fix** — `base.py` now builds urllib requests with `certifi`'s CA bundle
  (`SSL_CONTEXT`); a bare Python install on macOS ships no root certificates, so every
  shop-source HTTPS call failed with `CERTIFICATE_VERIFY_FAILED` outside Docker.

**Merge conflicts, both in files we'd already fixed (`shop.py`, `analyse_shop.py`):**
main didn't have our `searches_used` cost-counting fix from the previous merge, and had
independently kept using the old, undercounting `pages_fetched` for cost display while
adding real improvements of its own (graceful `write()` failure handling, a `self.place`
attribute for the new `similar_nearby()` competitor-finder, a better "page cap hit"
message). Resolved by combining both: kept every one of main's improvements, but pointed
their cost-reporting at our `searches_used` instead of `pages_fetched`. Also found the same
undercounting bug had propagated into the new `market.py`'s `gather_competitors()` (it
accumulated `pages_fetched`, missing the lookup cost for any *named* competitor) — fixed
there too, in the same merge commit.

Verified after merging: syntax-compiled and imported every backend module (all clean,
including the two new files `errors.py` and `market.py`) before committing. No live
API calls were needed to verify this merge — the conflicts were resolvable by reading the
code, and the credit-costly fix had already been verified live in the previous merge.

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
