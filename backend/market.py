"""Market scan: the "similar market" branch of the Gatherer, plus a summary
the Analyst can reason with.

For a shop: find the busiest places of the same kind nearby (or take the names
the caller gives), pull a small batch of each one's newest reviews, filter them
through the Checker, and ask Groq once for each competitor's strengths and
weaknesses. For a gathered week: the same summary over the market rows
gatherer_config.json already collected for that week.

Everything here is optional to the run: a competitor that can't be found or
fetched becomes a warning, and a failed summary still lists the competitors.
One Groq call covers every competitor, because the plan's 8,000 tokens per
minute is shared with the Scorer and one Analyst call per theme."""

import json
import random

from checker import check_reviews
from gatherer.gatherer import gather
from gatherer.schema import MARKET
from gatherer.sources import REGISTRY
from llm import call_llm, strip_code_fences

DEFAULT_COMPETITORS = 3
MAX_COMPETITORS = 5
# Per competitor: enough reviews to see a pattern, few enough to stay cheap.
# 8 on the first SerpApi page + 20 on each later one, so 4 pages reach 60.
REVIEWS_EACH = 60
MAX_PAGES_EACH = 4
# What the summary call reads per competitor (the rest only count as volume)
SAMPLE_EACH = 20
MAX_CHARS_PER_REVIEW = 150
MAX_POINTS = 3

SYSTEM_PROMPT = """You compare a business's local competitors using their customers' reviews.
For each competitor you are given, find what its customers praise (strengths) and what
they complain about (weaknesses). Only use what the reviews say. Be concrete and short:
"fast service at lunch", not "good experience".

Respond with ONLY a JSON object:
{"competitors": [{"name": "<exactly as given>",
                  "strengths": [{"point": "<under 8 words>", "evidence": "<a short quote from its reviews>"}],
                  "weaknesses": [{"point": "<under 8 words>", "evidence": "<a short quote from its reviews>"}]}]}
Give at most 3 strengths and 3 weaknesses per competitor, most mentioned first. Use an
empty list when the reviews show none."""


def find_competitors(own_source, names: list[str], location: str, n: int = DEFAULT_COMPETITORS,
                     warn=print) -> tuple[list[dict], bool]:
    """Named competitors when the caller gave some, otherwise places of the
    same kind near own_source (after it has fetched). Returns (competitors,
    discovered)."""
    names = [x.strip() for x in names if x and x.strip()][:MAX_COMPETITORS]
    if names:
        return [{"name": x, "place_id": None, "address": "", "rating": None,
                 "review_count": None, "category": None} for x in names], False
    try:
        return own_source.similar_nearby(n), True
    except Exception as e:
        warn(f"Couldn't find nearby competitors ({e}).")
        return [], True


def gather_competitors(competitors: list[dict], location: str, provider: str, since: str | None,
                       warn=print) -> tuple[dict[str, list[dict]], int]:
    """Verified reviews per competitor name, and the SerpApi searches spent.
    A competitor that fails or has nothing usable is dropped with a warning."""
    by_name, pages = {}, 0
    for c in competitors:
        # "Chai Point, Banjara Hills" already says where; don't append our location too
        source = REGISTRY["shop"](name=c["name"], location="" if "," in c["name"] else location,
                                  provider=provider,
                                  origin=MARKET, limit=REVIEWS_EACH, max_pages=MAX_PAGES_EACH,
                                  place_id=c.get("place_id"), since=since)
        errors: list = []
        reviews = gather([source], log=lambda *a: None, errors=errors)
        # searches_used, not pages_fetched: a named competitor (place_id=None)
        # needs an extra place-lookup search that pages_fetched doesn't count
        # (see shop.py) -- undercounted here too until this fix.
        pages += source.searches_used
        if not c.get("address") and source.place:  # a named competitor: fill in what Maps found
            c.update(address=source.place.get("address", ""), rating=source.place.get("rating"),
                     review_count=source.place.get("reviews"), category=source.place.get("type"))
        if reviews.empty:
            warn(f"Skipped competitor {c['name']!r}: "
                 + (f"{errors[0][1]}" if errors else "no reviews with text found") + ".")
            continue
        verified, _, _ = check_reviews(reviews.to_dict("records"))
        if not verified:
            warn(f"Skipped competitor {c['name']!r}: none of its {len(reviews)} reviews passed the Checker.")
            continue
        by_name[c["name"]] = verified
    return by_name, pages


def summarise(business: str, groups: dict[str, list[dict]], meta: dict[str, dict] | None = None,
              warn=print) -> list[dict]:
    """One Groq call: strengths and weaknesses for every competitor in groups
    (name -> verified reviews). meta adds address/rating/review_count per name.
    A failed call still returns every competitor, with empty lists and
    degraded=True, so the dashboard can say who was compared."""
    meta = meta or {}
    out = [{"name": name, "address": meta.get(name, {}).get("address", ""),
            "rating": meta.get(name, {}).get("rating"),
            "review_count": meta.get(name, {}).get("review_count"),
            "reviews_used": len(rows), "strengths": [], "weaknesses": [], "degraded": True}
           for name, rows in groups.items()]
    if not out:
        return out

    blocks = []
    for name, rows in groups.items():
        sample = random.sample(rows, min(SAMPLE_EACH, len(rows)))
        texts = [str(r.get("text", ""))[:MAX_CHARS_PER_REVIEW] for r in sample if r.get("text")]
        blocks.append(f"Competitor: {name}\nReviews:\n" + "\n".join(f"- {t}" for t in texts))
    prompt = (f"The business being analysed: {business}\n\n" + "\n\n".join(blocks))

    raw = call_llm(SYSTEM_PROMPT, prompt, fallback="")
    try:
        parsed = json.loads(strip_code_fences(raw))
        items = parsed.get("competitors") if isinstance(parsed, dict) else parsed
        if not isinstance(items, list):
            raise TypeError("no competitors list")
    except (json.JSONDecodeError, TypeError, AttributeError):
        warn("Couldn't summarise the competitors' reviews (Groq unavailable or an unusable reply); "
             "they're listed without strengths and weaknesses.")
        return out

    by_key = {_key(c["name"]): c for c in out}
    for item in items:
        if not isinstance(item, dict):
            continue
        c = by_key.get(_key(item.get("name")))
        if c is None and len(out) == 1:  # the model reworded the only name
            c = out[0]
        if c is None:
            continue
        c["strengths"], c["weaknesses"] = _points(item.get("strengths")), _points(item.get("weaknesses"))
        c["degraded"] = False
    missed = [c["name"] for c in out if c["degraded"]]
    if missed:
        warn(f"No strengths or weaknesses came back for {', '.join(missed)}.")
    return out


def context_for_analyst(competitors: list[dict]) -> str:
    """The compact text the Analyst gets with every theme. Kept short on
    purpose: it is repeated in each per-theme call."""
    lines = []
    for c in competitors:
        if c.get("degraded"):
            continue
        rating = f", {c['rating']}★" if c.get("rating") else ""
        good = "; ".join(p["point"] for p in c["strengths"]) or "nothing stands out"
        bad = "; ".join(p["point"] for p in c["weaknesses"]) or "nothing stands out"
        lines.append(f"- {c['name']}{rating}. Praised for: {good}. Criticised for: {bad}.")
    return "\n".join(lines)


def _key(name) -> str:
    return " ".join(str(name or "").lower().split())


def _points(items) -> list[dict]:
    points = []
    for p in items if isinstance(items, list) else []:
        if isinstance(p, str):
            p = {"point": p}
        if isinstance(p, dict) and str(p.get("point", "")).strip():
            points.append({"point": str(p["point"]).strip(), "evidence": str(p.get("evidence", "")).strip()})
    return points[:MAX_POINTS]
