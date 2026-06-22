# Using job-hunter

A practical guide to running the tool, and to adding your own **persona**.

## Mental model

The tool turns a **persona** (an anonymised candidate description) into a ranked
shortlist of jobs. Nothing about you is hard-coded — everything that shapes the search
and the scoring lives in one YAML file per persona under `data/personas/`.

```
data/personas/<id>.yaml   ─▶   3 phases   ─▶   data/roles/<id>/<date>/
   (who you are)              (collect/enrich/rank)   (your ranked shortlist)
```

You can keep several personas (e.g. one tuned for quant roles, one for ML) and run
each independently. Each persona's results are stored separately under its own `id`.

Commands are marked 🟢 (read-only / safe to repeat) or 🟠 (writes files).

## Quick start

```bash
uv sync                                # 🟢 install
uv run job-hunter run --persona example # 🟠 run the bundled demo persona
```

Output lands in `data/roles/example/<date>/`:
- `index.md` — the ranked shortlist as a table
- `roles/<score>__<company-role>__<id>.md` — one file per role, full detail
- `roles.json` — machine-readable dump

## Creating your own persona

A persona is the only thing you need to make this work for *you*.

1. **Copy the template** (🟠 — it creates a new file):

   ```bash
   cp data/personas/_template.yaml data/personas/jordan.yaml
   ```

2. **Fill it in.** Open `data/personas/jordan.yaml` and replace every `< ... >`
   placeholder. The fields, in order of importance:

   | Field | What it does |
   |---|---|
   | `id` | Unique handle (a-z, 0-9, dashes). Selects the persona and names its output dir. |
   | `lanes` | The career tracks you target. `title_terms` match the job **title**; `boost_skills` match the **description**. The biggest lever on relevance. |
   | `skills` | Your real skills in three honesty buckets (`strong` > `working` > `learning`). Each match adds to the fit score. |
   | `target_countries` | Where you want to work. Everything else is penalised hard. |
   | `role_gate` | Hard title filter: a job must contain a `core` term and no `exclude` term. |
   | `seniority` | Rewards a matching level in the title, penalises too-junior/too-senior. |
   | `negative_signals` | Phrases that kill fit (wrong stack, blockers, wrong domain). |

   Keep every list **lowercase**. Short tokens like `"ml "` / `"ai "` keep the trailing
   space on purpose so they match as whole words.

3. **Run it** (🟠):

   ```bash
   uv run job-hunter run --persona jordan
   ```

   Results go to `data/roles/jordan/`. Your persona file is **git-ignored**, so your
   real details never get committed (only `_template.yaml` and `example.yaml` are tracked).

> Honesty matters: the fit score is only as truthful as the skills you list. Inflating
> `strong` just produces optimistic numbers, not better jobs.

## The three phases

Each phase reads the previous one's artifact from `data/work/<persona>/`, so you can
re-run any phase alone — e.g. tweak scoring and only re-rank, with no re-scraping.

| Phase | Command | Does | Writes |
|---|---|---|---|
| 1 | 🟠 `job-hunter collect` | Pull free APIs → dedup → location/reputation/role gates → prescreen heuristic | `phase1_candidates.json` |
| 2 | 🟠 `job-hunter enrich` | Re-fetch live pages; optional Claude Haiku scores fit + salary | `phase2_enriched.json` |
| 3 | 🟠 `job-hunter rank` | Blend heuristic + AI scores, sort | role files in `data/roles/<persona>/` |

`job-hunter run` does all three. Add `--persona <id>` to any of them (before or after
the subcommand both work).

## Common options

```bash
# AI enrichment of the top candidates (needs ANTHROPIC_API_KEY in .env)
uv run job-hunter run --persona jordan --enrich-top 25   # LLM on by default; add --no-llm to skip

# Cast a wider net
uv run job-hunter run --persona jordan --prescreen-min 40 --include-unknown --anywhere

# Pick specific sources
uv run job-hunter collect --persona jordan --providers ats themuse

# Retune scoring without re-scraping
uv run job-hunter rank --persona jordan
```

## Optional API keys

Copy `.env.example` to `.env` and fill in what you have (all optional):

- **`ANTHROPIC_API_KEY`** — enables the default Claude Haiku enrichment (fit notes + salary inference; `--no-llm` to skip).
- **`ADZUNA_APP_ID` / `ADZUNA_APP_KEY`** — adds Adzuna (best on-the-ground coverage of your target countries + salary).

`.env` is git-ignored.

## Tuning

- **Target companies:** the reputation gate is curated in `src/job_hunter/reputation.py`.
- **Company career boards:** add an `(ats, slug, name)` row to `BOARDS` in
  `src/job_hunter/providers/ats.py` (Greenhouse / Lever / Ashby). A wrong slug just
  returns nothing.
- **Scoring weights:** constants in `src/job_hunter/scoring/heuristic.py`.
- **A new job source:** add a `Provider` subclass in `src/job_hunter/providers/` and
  register it in `providers/__init__.py`.
