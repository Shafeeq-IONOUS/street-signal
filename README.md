# Street Signal

**Is it just me, or is my street being ignored?**

A resident asks about their street in plain English and gets a grounded, cited answer
from Boston's own 311 records — plus a 3D priority board where neighbours can back the
issues that matter.

Built for [RAG the City](https://the-open-accelerator.com/hackathon/upcoming/RAGtheCityHack/),
Boston, 22 August 2026. Track B — The Experience.

---

## What it does

You report the rats. Weeks later an email says **Closed**. Nothing has changed, and you're
left with two questions nobody can answer: *is this normal for a city?* and *did anything
actually happen?*

Street Signal answers both in one sentence:

> **No — 9 residents reported rodent activity on 328 Dartmouth St in 2025.**
> The city logged 4 more itself. ISD handles these.
> **12 of the cases there closed as "noted only"** — recorded, with no fix logged.

Every figure opens the city's own record for that case.

---

## Run it

No install, no build server, no API key.

```bash
cd app
python3 -m http.server 8900
open http://localhost:8900/
```

That's it. The page carries its own data, its own map, and its own retrieval.

### Optional — the local model

Free-text reports ("the back alley is piled with bags and it smells") get classified by
[Granite 3.1 8B](https://ollama.com/library/granite3.1-dense) running on your machine:

```bash
ollama pull granite3.1-dense:8b
ollama serve
```

Without it, the same keyword router the search uses takes over, and the interface says
which one decided. The model only ever picks a label — it never writes a record.

---

## Rebuild the data

The two large inputs are gitignored (146 MB and 16 MB). To regenerate:

```bash
# 1. Boston's 311 export for 2025 — 267,187 rows
curl -sL --http1.1 --retry 5 --retry-all-errors \
  "https://data.boston.gov/datastore/dump/9d7c2214-4709-478a-a2e8-fb2020a5bb94?format=csv" \
  -o data_311_2025.csv

# 2. Roll those rows into readable cards — about 4 seconds, zero model calls
python3 cards/build_cards.py

# 3. Rebuild the single-file app
python3 - <<'PY'
s = open('app/shell3.html').read()
for tok, path in [("__THREE__","vendor/three.min.js"), ("__ORBIT__","vendor/OrbitControls.js"),
                  ("__CATS__","app/categories.js"), ("__MAP3D__","app/map3d.js"),
                  ("__CORPUS__","app/corpus_embed.json"), ("__PROPERTY__","app/property_embed.json"),
                  ("__HOODS__","app/hoods_embed.json"), ("__SEED__","app/seed_embed.json")]:
    s = s.replace(tok, open(path).read(), 1)
open('app/index.html','w').write(s)
PY
```

---

## How it works

The 311 export has **no prose in it**. 267,187 rows carry only short category codes —
2,982 distinct titles, of which the top thirty cover 84.9% of every row, and one
(`Parking Enforcement`) is 60,641 identical strings. Embed the rows and you get tens of
thousands of near-identical vectors: retrieval becomes a coin flip and the citations mean
nothing even though they're real.

So we don't index rows. `cards/build_cards.py` rolls them into **8,898 short readable
write-ups** — one per street-and-problem, one per problem — that have entities, numbers
and time in them, each carrying the case IDs it was built from.

```
question
  → ① classify intent      out of scope or personal → refuse, never search
  → hard filters           street · category · residents only, from THIS turn only
  → stage 1                citywide category card
  → stage 2                street-level card inside that category
  → ② sensitivity gate     address-level detail withheld unless asked for
  → score floor            no match → "I don't have a source I trust"
  → ③ output               every claim bound to a field, or it isn't written
```

The three numbered guardrails render on screen as a live strip, so you can watch which
one fired.

| Layer | What it is |
|---|---|
| Data | 8,898 cards from 267,187 rows, parcel facts for 58 streets, 26 neighbourhood polygons — all baked in |
| Retrieval | Plain JavaScript. Filters → two stages → sensitivity gate → score floor |
| Answer | Assembled from counted fields, never generated |
| Map | Three.js extruded from the city's own GeoJSON — no tile server |
| State | `localStorage` — votes, reports, points |
| LLM | Granite 3.1 8B on local Ollama, optional, keyword fallback |

---

## Two decisions worth knowing

**Residents are counted separately from city staff.** 57% of the 311 file is city
employees logging their own rounds. Without that split the app would say *"eleven
neighbours reported this too"* when seven were an inspector — the difference between
solidarity and a warm lie.

**The priority board adds a severity field the city doesn't have.** A rat infestation and
a misplaced recycling bin enter Boston's queue with the same clock. P1–P4 answers *who
should touch this*, never *is this real*. The first ranking let parking enforcement (22%
of the file) bury everything; crowd size now goes through a log so tier does the work.
Top 40 is 24 safety + 16 habitability, zero parking.

---

## Honest limits

- **Granite runs locally only.** Published to a static host it falls back to keyword
  classification. The prose is assembled from fields either way, which is why citations
  can't drift.
- **Property Assessment covers 58 streets**, not all of Boston — their API caps at 32,000
  rows and blocks `NULLIF`.
- **Approximate street matches say so.** "Beacon St" can land on a nearby intersection;
  the answer flags it rather than passing another street's numbers off as yours.
- **Reports stay on the device.** This is a community signal, not a filing with the City.
  Real reports still go to [311](https://311.boston.gov).
- **WebGL is required** for the map.

---

## Data

- [311 Service Requests](https://data.boston.gov/dataset/311-service-requests) — Analyze Boston
- [Property Assessment](https://data.boston.gov/dataset/property-assessment) — Analyze Boston
- [Neighborhood Boundaries](https://data.boston.gov/dataset/bpda-neighborhood-boundaries) — BPDA

Unofficial community tool. Not affiliated with the City of Boston.
