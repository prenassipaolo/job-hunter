# job-hunter

A **persona-driven** job hunter. You describe a candidate once — in an anonymised
`persona` file — and the tool finds high-fit roles across **Switzerland, Ireland, the
Netherlands and the UK**, scores how strong a candidate the persona is for each one, and
writes a file per role with the link, salary range (when available) and an estimated
**fit probability**.

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
Phase 1  collect   free job APIs ─▶ dedup ─▶ location gate (CH/IE/NL/UK/remote)
                    ─▶ reputation gate ─▶ role-type gate (dev/quant/DS only)
                    ─▶ prescreen heuristic score        ──▶ phase1_candidates.json
Phase 2  enrich     re-fetch each live page ─▶ Claude Haiku extracts salary/seniority
                    & scores fit (heuristic fallback if no key)  ──▶ phase2_enriched.json
Phase 3  rank       blend heuristic + AI ─▶ sort  ──▶ roles/*.md + index.md + roles.json
```

- **Sources (no API key needed):** TheMuse, RemoteOK, Arbeitnow, Jobicy, and **ats**
  — company career boards (Greenhouse / Lever / Ashby) pulled directly from your
  curated reputable employers (Point72, IMC, OpenAI, Stripe, Datadog, Celonis, …).
  Edit the board list in `src/job_hunter/providers/ats.py`.
- **Source (optional key):** Adzuna — best salary + CH/IE/NL/UK coverage. Add free
  keys in `.env` and it switches on automatically.
- **Scoring is hybrid:** a transparent offline heuristic plus **Claude Haiku**
  enrichment (cheapest model) on the top roles for a candid fit note and salary
  inference. The LLM runs **by default** in the full flow (results are cached); pass
  `--no-llm` to skip it, and `--refresh` to ignore caches.

### What the fit score means

A 0–100 estimate of how strong a candidate the persona is for the role — roughly the
chance of clearing the CV screen into an interview. It is a heuristic proxy, not a promise.
Every role file shows the full point breakdown (lane relevance, skills, location,
seniority, negatives, reputation) so you can sanity-check and retune it.

Bands: **Strong ≥70 · Good ≥55 · Moderate ≥40 · Stretch <40**.

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
# Run all three phases for a persona (keyless sources, reputable employers, CH/IE/NL/UK + remote)
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

## Tuning it

- **Add/remove target companies:** edit the tiers in `src/job_hunter/reputation.py`.
- **Reweight scoring:** edit the constants in `src/job_hunter/scoring/heuristic.py`
  and the skill/lane lists in your persona file under `data/personas/`.
- **Add a job source:** drop a `Provider` subclass in `src/job_hunter/providers/`
  and register it in `providers/__init__.py`.
- **Add a company board:** append an `(ats, slug, name)` row to `BOARDS` in
  `providers/ats.py`. A wrong slug just returns nothing — no harm in trying one.

## Notes & honesty

- This scrapes public/free job APIs, not LinkedIn (LinkedIn's terms forbid scraping
  and it rarely exposes salary). The provider interface makes adding sources easy.
- Keyless remote APIs skew toward remote/tech roles; **Adzuna keys** materially
  improve on-the-ground CH/IE/NL/UK coverage and salary data — worth the 2-minute
  signup.
- The reputation list is curated and finite; a great employer it doesn't know yet will
  be filtered out until you add it. Use `--include-unknown` to inspect the long tail.
