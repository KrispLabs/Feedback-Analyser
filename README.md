# Feedback Analyser

Give it a business name and a location. It scrapes that business's public
reviews, throws away the junk, groups what's left into themes, and scores each
theme from **−5 to +5** with a reason and a concrete next step — so an owner
sees *what to fix first* and *what not to break*, not just a star rating.

It also remembers. Every run is stored, so the next one can say *"crowding was
flagged 10 times last month, 5 this month"* instead of restating one batch.

```
$ python analyse_shop.py "Niloufer Cafe" "Hitech City"

  +5   Excellent tea and bun maska   (12 mentions)
       why   All 12 mentions praise the chai and bun maska as the highlight,
             describing them as the best they've had. This is the single
             biggest strength right now.
       do    Continue preparing the Irani tea and bun maska exactly as they
             are — same recipes, sourcing, and preparation.

  -4   Overpriced / hype   (13 mentions)
       why   Thirteen customers called the pricing too high, with chai at
             ₹150–250 and repeated "not worth the hype" comments...
       do    Introduce value bundles (tea + bun combo) and communicate them
             in-store, then monitor price perception.
```

---

## How it works

Five stages. Each one hands the next a plain list of dicts, so any stage can be
swapped without touching the others.

```
  name + location
        │
        ▼
 ┌─────────────┐   Google Maps / Play Store / App Store / Kaggle CSV
 │  GATHERER   │   → one normalised table, written to data/cleaned/reviews.csv
 └─────────────┘
        │  id, source, origin, business, date, week, rating, text, …
        ▼
 ┌─────────────┐   rule-based, no LLM: duplicates, <4 words,
 │   CHECKER   │   repeated-phrase spam, gibberish
 └─────────────┘
        │  verified reviews + a rejected count
        ▼
 ┌─────────────┐   one Groq call: reads a sample, returns recurring
 │   SCORER    │   themes with a name, mention count and quotes
 └─────────────┘
        │  [{name, count, samples}]
        ▼
 ┌─────────────┐   one Groq call per theme, plus recall of past runs
 │   ANALYST   │   → score −5..+5, reasoning, next_step
 └─────────────┘
        │
        ▼
 ┌─────────────┐   stores this run so the next one can spot trends
 │  HINDSIGHT  │
 └─────────────┘
```

| Stage | File | What it does |
|---|---|---|
| Gatherer | `backend/gatherer/` | Pulls reviews from a shop (Google Maps), an app (Play/App Store) or a CSV into one table |
| Checker | `backend/checker.py` | Rule-based filter. No LLM — deterministic and free |
| Scorer | `backend/scorer.py` | Groq groups reviews into themes with counts and quotes |
| Analyst | `backend/analyst.py` | Groq scores each theme −5..+5 with reasoning, using past runs |
| Memory | `backend/memory.py` | Hindsight Cloud — semantic recall across runs |
| API | `backend/api.py` | FastAPI wrapper for the mobile app |

### The −5..+5 scale

A plain sentiment score doesn't tell an owner what to do on Monday. This one is
a triage queue:

| Score | Meaning |
|---|---|
| **+5** | The single best thing. Don't change it |
| +1..+4 | Real strengths, ranked by how much they matter |
| −1..−4 | Real problems, ranked by urgency |
| **−5** | Fix this before anything else |

### Why memory matters

Themes get reworded between runs — "Pricing and Affordability" one month,
"pricing reasonableness" the next. Hindsight's recall is semantic, so it bridges
the rename and the Analyst still cites the earlier figure. That's the difference
between a monthly snapshot and an actual trend.

---

## Setup

Needs Python 3.12+.

```bash
git clone https://github.com/KrispLabs/Feedback-Analyser.git
cd Feedback-Analyser/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in the repo root and fill it in:

```ini
GROQ_API_KEY=          # required — console.groq.com
HINDSIGHT_API_KEY=     # required — hindsight.vectorize.io
SERPAPI_API_KEY=       # for shop reviews — serpapi.com (250 free searches/month)
GOOGLE_MAPS_API_KEY=   # alternative to SerpApi (capped at 5 reviews per shop)
```

`.env` is gitignored — never commit it. For local CLI runs, export it first:

```bash
set -a && . ../.env && set +a
```

Docker picks `.env` up on its own:

```bash
docker compose up        # serves the API on :8000
```

> **macOS note:** a bare venv ships no root certificates, so every HTTPS source
> fails with `CERTIFICATE_VERIFY_FAILED`. Fix once with
> `pip install certifi && export SSL_CERT_FILE=$(python -c "import certifi;print(certifi.where())")`,
> or just use Docker.

---

## Usage

### Analyse a business by name and location

```bash
python analyse_shop.py                                   # prompts for both
python analyse_shop.py "Niloufer Cafe" "Hitech City"
python analyse_shop.py "Niloufer Cafe" "Hitech City" --months 6 --limit 300
```

| Flag | Default | What it does |
|---|---|---|
| `--months N` | `3` | Only analyse the last N months. `0` = all time |
| `--limit N` | `200` | Max reviews **with text** to gather |
| `--provider` | `serpapi` | `serpapi` (hundreds of reviews) or `places` (Google's own API, max 5) |
| `--max-pages N` | `15` | Ceiling on billable SerpApi searches, so one run can't drain your quota |
| `--run N` | `1` | Numbers this run so later runs compare against it |
| `--no-store` | off | Don't write to Hindsight |

Each business should get its own Hindsight bank, or a cafe's themes pollute a
telecom's recall:

```bash
HINDSIGHT_BANK_ID=niloufer-cafe python analyse_shop.py "Niloufer Cafe" "Hitech City"
```

### Just gather, without analysing

```bash
python -m gatherer shop "Niloufer Cafe" "Hitech City" --since 2026-07-01
python -m gatherer --config gatherer_config.json          # apps + CSV datasets
python run_week.py 2                                      # analyse one ISO week
python run_week.py --weeks                                # list available weeks
```

Gathered reviews append to `data/cleaned/reviews.csv`. Review IDs are stable
hashes, so re-gathering the same business updates rows instead of duplicating.

---

## API — for the frontend

```bash
cd backend && uvicorn api:app --host 0.0.0.0 --port 8000
# or: docker compose up
```

Interactive docs are generated automatically at **`/docs`** (Swagger) and
**`/redoc`** — those are always current, so trust them over this file if they
ever disagree.

### `GET /health`

Liveness check. Hits no external service.

```json
{ "status": "ok" }
```

### `POST /shops/analyse` — the main flow

Body:

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | *required* | `"Niloufer Cafe"` |
| `location` | string | `""` | `"Hitech City, Hyderabad"` |
| `months` | int | `3` | Last N months. `0` = all time. Max 120 |
| `limit` | int | `200` | Max reviews with text. 1–1000 |
| `provider` | string | `"serpapi"` | `"serpapi"` or `"places"` |
| `store` | bool | `true` | Write to Hindsight for trend recall |
| `run_number` | int | `1` | Later runs compare against earlier ones |

```bash
curl -X POST http://localhost:8000/shops/analyse \
  -H 'Content-Type: application/json' \
  -d '{"name":"Niloufer Cafe","location":"Hitech City","months":3}'
```

**`200`** — the whole dashboard payload:

```json
{
  "week": 3,
  "business": "Niloufer Cafe",
  "location": "Hitech City",
  "period": "2026-07-18 to 2026-09-28",
  "rejected_count": 10,
  "rejected_by_reason": { "too_short": 10 },
  "themes": [
    {
      "name": "Excellent tea and bun maska",
      "count": 12,
      "score": 5,
      "samples": [
        "Absolutely loved this place! The chai and bun maska were easily the highlight...",
        "A legendary spot for a proper Irani tea and bun maska...",
        "Good tea... Tasty maskabun."
      ],
      "reasoning": "All 12 mentions in the period specifically praise the chai and bun maska as the highlight of the cafe... indicating the single biggest strength right now.",
      "next_step": "Continue preparing the Irani tea and bun maska exactly as they are — maintain the same recipes, sourcing and preparation methods."
    }
  ]
}
```

### `POST /weeks/{week_number}/run`

Same payload shape, but for one ISO week of whatever the Gatherer last
collected. `week_number` is 1-indexed into the weeks present in the CSV (1 =
earliest). Used for the weekly-trend view rather than one-off lookups.

### Response fields

| Field | Type | UI hint |
|---|---|---|
| `business`, `location` | string | Header |
| `period` | string | `"2026-07-18 to 2026-09-28"` — show it, the scores only describe this window |
| `rejected_count` | int | "10 reviews filtered out" |
| `rejected_by_reason` | object | `{"too_short": 10}` — keys are `too_short`, `duplicate`, `repeated_phrase`, `gibberish` |
| `themes[].name` | string | Card title |
| `themes[].count` | int | How many reviews mention it |
| `themes[].score` | int | **−5..+5.** Sort ascending: worst first |
| `themes[].samples` | string[] | 1–3 real quotes. Good for an expandable card |
| `themes[].reasoning` | string | Why this score. A paragraph |
| `themes[].next_step` | string | What to do. A paragraph |

`themes` comes back unsorted — sort by `score` in the client. Split at zero for
a two-column "Fix these / Protect these" layout.

### Errors

| Status | Meaning | What to show |
|---|---|---|
| `404` | Business not found, or every review was filtered out | "Couldn't find reviews for that business — try adding the city" |
| `422` | Bad request body (e.g. `months: 999`) | Field validation. `detail[0].msg` has the reason |
| `502` | Groq / SerpApi / Hindsight failed, or a rate limit | "Couldn't analyse right now, try again shortly" — retriable |

### ⚠ These endpoints are slow — plan for it

**60–120 seconds is normal**, and the request is synchronous. It scrapes
reviews, then makes one Groq call *per theme*. A measured run took 27s for 6
themes; a bigger one took 89s.

For a mobile client:

- **Set the client timeout to at least 180s.** The default 30–60s will abort a
  perfectly healthy request.
- **Show real progress**, not a spinner — "Finding reviews… / Filtering… /
  Scoring themes…" — or it reads as frozen.
- **Don't fire it on every keystroke.** One call per explicit search.
- **Cache by `(name, location, months)`.** Re-running the same business costs
  real money in Groq tokens and SerpApi searches.

If this becomes a problem, the fix is a job queue: `POST` returns a job id
immediately and the client polls. Not built yet.

### CORS

Currently `allow_origins=["*"]` to unblock local development. **Tighten it to
the real frontend origin before shipping** (`backend/api.py`).

---

## Cost and limits

Every run spends real quota, on three services:

| Service | Free tier | Per run |
|---|---|---|
| Groq | 200,000 tokens/day | 1 call for themes + 1 per theme (~7–9 total) |
| SerpApi | 250 searches/month | ~1 search per 20 reviews (6–9 typical) |
| Hindsight | — | 1 store + 1 recall per theme |

Guards already in place: `--max-pages` caps SerpApi searches per run; `--months`
stops paginating once reviews fall outside the window; the Checker is pure rules
so filtering costs nothing; and the Scorer reads a *sample* to find themes, then
matches locally.

**If Groq's daily quota runs out**, the Analyst returns `score: 0` with
`reasoning: "LLM unavailable, defaulted to neutral."` The HTTP call still
succeeds with a `200`. The CLI flags these as `⚠ NOT A REAL SCORE` — a client
should check for that reasoning string rather than render six confident zeros.

---

## Repo layout

```
backend/
  analyse_shop.py      name + location → full analysis (CLI and API entry point)
  run_week.py          same pipeline over one ISO week
  api.py               FastAPI wrapper
  gatherer/
    gatherer.py        orchestrates sources → one cleaned CSV
    schema.py          the row format every source normalises into
    cleaning.py        text/date/rating normalisation, stable IDs
    sources/
      shop.py          Google Maps via SerpApi or Google Places
      playstore.py     Google Play
      appstore.py      Apple RSS
      csv_source.py    Kaggle / offline datasets
  checker.py           rule-based filter
  scorer.py            LLM theme discovery
  analyst.py           LLM scoring + reasoning
  memory.py            Hindsight store / recall
  llm.py               shared Groq helper: retries, rate-limit backoff, fallbacks
  config.py            key loading (env → keys.csv)
data/cleaned/          gathered reviews (gitignored)
NOTES.md               engineering log: decisions, bugs found, what's verified
```

`NOTES.md` is the detailed working record — every bug found against real data
and how it was fixed. Worth reading before changing any stage.
