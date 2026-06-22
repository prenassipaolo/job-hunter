"""Phase-2 caching: a page is fetched once, then served from cache (until --refresh)."""

import importlib
import json

from job_hunter.phases.enrich import EnrichConfig, enrich

# NOTE: job_hunter.phases re-exports the `enrich` function, which shadows the submodule
# under attribute access. importlib.import_module returns the real module object from
# sys.modules, so we can patch the name `fetch_page_text` bound inside it.
enrich_mod = importlib.import_module("job_hunter.phases.enrich")

PERSONA = "lanes:\n  - id: x\n    title_terms: [engineer]\n"
JOBS = [
    {"source": "ats", "title": "Engineer", "company": "Optiver", "url": "http://x/1"},
    {"source": "ats", "title": "Quant", "company": "IMC", "url": "http://x/2"},
]


def _setup(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "phase1_candidates.json").write_text(json.dumps(JOBS), encoding="utf-8")
    persona = tmp_path / "p.yaml"
    persona.write_text(PERSONA, encoding="utf-8")
    return str(persona), str(work)


def test_pages_cached_then_refreshed(tmp_path, monkeypatch):
    persona, work = _setup(tmp_path)
    calls = {"n": 0}

    def fake_fetch(url, *a, **k):
        calls["n"] += 1
        return f"text for {url}"

    monkeypatch.setattr(enrich_mod, "fetch_page_text", fake_fetch)
    cfg = EnrichConfig(profile_path=persona, work_dir=work, top_n=10, use_llm=False)

    enrich(cfg)
    assert calls["n"] == 2            # both pages fetched on the first run

    enrich(cfg)
    assert calls["n"] == 2            # second run: served entirely from cache

    enrich(EnrichConfig(profile_path=persona, work_dir=work, top_n=10, use_llm=False, refresh=True))
    assert calls["n"] == 4            # --refresh re-fetches both
