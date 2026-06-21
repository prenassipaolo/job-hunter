"""The three pipeline phases. Each reads the previous phase's artifact from disk.

    collect (phase 1)  -> phase1_candidates.json
    enrich  (phase 2)  -> phase2_enriched.json
    rank    (phase 3)  -> roles/*.md + index.md + roles.json

Run them individually or chain them with the `run` orchestrator in pipeline.py.
"""

from .collect import collect
from .enrich import enrich
from .rank import rank

__all__ = ["collect", "enrich", "rank"]

PHASE1_FILE = "phase1_candidates.json"
PHASE2_FILE = "phase2_enriched.json"
