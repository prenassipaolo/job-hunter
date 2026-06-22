# job-hunter

A **persona-driven** job hunter. You describe a candidate once — in an anonymised
`persona` file — and the tool finds high-fit roles in the **countries you choose**,
scores how strong a candidate the persona is for each one, and writes a file per role
with the link, salary range (when available) and an estimated **fit probability**.

Where roles are searched and how locations rank is fully configurable — countries and
cities are tiered (1 = best) in `src/job_hunter/locations.py`. It ships tuned for
**Switzerland, Ireland, the Netherlands and the UK** (tier 1), with Germany, Italy, the
US and more at lower tiers; edit `COUNTRY_TIERS` / `CITY_TIERS` to make it yours.

It only keeps **reputable employers** — top trading firms, big tech, serious fintech
and well-regarded banks/research labs — the kind of places with real room to learn and
grow. Random unknown companies are filtered out by default.

Each persona has an `id`; you run a search for a specific persona and its results are
stored under that id. A blank **`_template.yaml`** and a fictional **`example.yaml`** ship
in `data/personas/` — copy the template to make your own. **New here? Read
[docs/GUIDE.md](docs/GUIDE.md).**

The bundled example persona targets three lanes (yours can be anything):

1. **Quant Developer / Model Engineering**
2. **Applied AI / ML Engineering**
3. **Data Scientist / Data Platform Engineering**

## How it works — three phases that flow into each other

Each phase reads the previous phase's artifact from disk, so they run independently or
chained. Cheap fixed rules do the bulk filtering first; the AI only ever looks at the
small, clean survivor set.

```
Phase 1  collect   free job APIs ─▶ dedup ─▶ location gate (tiered countries/remote)
                    ─▶ reputation gate ─▶ role-type gate (from the persona's lanes)
                    ─▶ prescreen heuristic score        ──▶ phase1_candidates.json
Phase 2  enrich     re-fetch each live page ─▶ Claude Haiku scores subjective features
                    (responsibilities, interest) + salary  ──▶ phase2_enriched.json
Phase 3  rank       re-score with AI features ─▶ sort  ──▶ roles/*.md + index.md + roles.json
```

Scoring is one **logistic** over weighted features (`src/job_hunter/scoring/features.py`):
the heuristic fills objective features (skills overlap, location, recency, …) for every
job; the LLM fills subjective ones (responsibilities, interest) for the worthy few. Both
feed the same score, so it's bounded 0–100 and fully explainable in each role file.

- **Sources (no API key needed):** TheMuse, RemoteOK, Arbeitnow, Jobicy, and **ats**
  — company career boards (Greenhouse / Lever / Ashby) pulled directly from your
  curated reputable employers (Point72, IMC, OpenAI, Stripe, Datadog, Celonis, …).
  Edit the board list in `src/job_hunter/providers/ats.py`.
- **Source (optional key):** Adzuna — best salary + on-the-ground coverage for your
  target countries. Add free keys in `.env` and it switches on automatically.
- **Scoring is hybrid:** a transparent offline heuristic plus **Claude Haiku**
  enrichment (cheapest model) on the top roles for a candid fit note and salary
  inference. The LLM runs **by default** in the full flow (results are cached); pass
  `--no-llm` to skip it, and `--refresh` to ignore caches.

### What the fit score means

A 0–100 estimate of how strong a candidate the persona is for the role — roughly the
chance of clearing the CV screen into an interview. It is a model output, not a promise.
Each role file shows every **feature** (skills overlap, title fit, location, seniority,
reputation, recency, no-wrong-stack, and — once enriched — the AI's responsibilities &
interest scores) with its weight and contribution, so you can sanity-check and retune it.

Bands: **Strong ≥80 · Good ≥62 · Moderate ≥42 · Stretch <42**.

## Setup

```bash
cd job-hunter
uv sync                 # core install
uv sync --extra dev     # + pytest/ruff
uv sync --extra llm     # + anthropic (needed for LLM enrichment, which is on by default)
cp .env.example .env     # optional: add ADZUNA_* and/or ANTHROPIC_API_KEY
```

## Usage

Pick a persona with `--persona <id>` (defaults to `example`). It works before or after
the subcommand. Make your own first: `cp data/personas/_template.yaml data/personas/<id>.yaml`.

```bash
# Run all three phases for a persona (keyless sources, reputable employers, tiered countries + remote)
uv run job-hunter run --persona example

# Run phases individually — each reads the previous artifact from data/work/<persona>/
uv run job-hunter collect --persona example      # phase 1 -> phase1_candidates.json
uv run job-hunter enrich  --persona example      # phase 2 -> phase2_enriched.json (Claude Haiku, cached)
uv run job-hunter rank    --persona example --top 40  # phase 3 -> role files

# Full run with AI enrichment of the top 25 candidates
uv run job-hunter run --persona example --enrich-top 25   # LLM on by default; --no-llm to skip

# Cast a wider net
uv run job-hunter run --persona example --prescreen-min 40 --include-unknown --anywhere

# Pick specific sources
uv run job-hunter collect --persona example --providers ats themuse adzuna
```

Tweak just the scoring? Edit the heuristic, then re-run only `rank` — no re-scraping:

```bash
uv run job-hunter rank --persona example
```

Output lands in `data/roles/<persona>/<date>/`:

- `index.md` — ranked shortlist table (fit, company, role, country, salary, link)
- `roles/<score>__<company-role>__<id>.md` — one file per role with full detail
- `roles.json` — machine-readable dump of everything

## Project layout

```
job-hunter/
├── pyproject.toml              # uv / packaging
├── .env.example                # optional API keys
├── docs/GUIDE.md               # how to use the repo + add personas
├── data/
│   ├── personas/               # _template.yaml + example.yaml (tracked); yours git-ignored
│   ├── work/<persona>/         # phase artifacts (phase1/phase2 JSON)
│   └── roles/<persona>/<date>/ # final generated output
├── src/job_hunter/
│   ├── cli.py                  # subcommands: run / collect / enrich / rank (+ --persona)
│   ├── pipeline.py             # chains the three phases
│   ├── phases/                 # collect.py · enrich.py · rank.py
│   ├── models.py               # Job dataclass
│   ├── profile.py              # persona loader
│   ├── reputation.py           # curated reputable-employer tiers
│   ├── pagefetch.py            # phase-2 live-page re-fetch
│   ├── providers/              # one module per job source
│   └── scoring/                # heuristic.py (default) + llm.py (Claude Haiku)
└── tests/
```

## Customise your search — where to edit what

- **Who you are (skills, lanes, seniority, stretch titles):** your persona file in
  `data/personas/`. This is the biggest lever — skills overlap dominates the score.
- **Which countries/cities, and how they rank:** `COUNTRY_TIERS` / `CITY_TIERS` in
  `src/job_hunter/locations.py` (1 = best; e.g. `"Switzerland": 1`). The location *gate*
  keeps any tiered country (or remote); tier only affects ranking.
- **Which employers count as reputable:** the tiers in `src/job_hunter/reputation.py`.
- **Feature weights / the scoring model:** `src/job_hunter/scoring/features.py`.
- **Add a job source:** a `Provider` subclass in `src/job_hunter/providers/`, registered
  in `providers/__init__.py`.
- **Add a company board:** append an `(ats, slug, name)` row to `BOARDS` in
  `providers/ats.py`. A wrong slug just returns nothing — no harm in trying one.

## Notes & honesty

- This scrapes public/free job APIs, not LinkedIn (LinkedIn's terms forbid scraping
  and it rarely exposes salary). The provider interface makes adding sources easy.
- Keyless remote APIs skew toward remote/tech roles; **Adzuna keys** materially
  improve on-the-ground coverage of your target countries and salary data — worth the
  2-minute signup.
- The reputation list is curated and finite; a great employer it doesn't know yet will
  be filtered out until you add it. Use `--include-unknown` to inspect the long tail.
