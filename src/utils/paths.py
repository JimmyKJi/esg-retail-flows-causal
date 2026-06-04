"""Canonical filesystem paths for the project.

Importing this module guarantees the data/ and paper/ output directories
exist, so ingestion and estimation code never has to mkdir defensively.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA = REPO_ROOT / "data"
DATA_RAW = DATA / "raw"            # never hand-edited; download scripts only (gitignored)
DATA_INTERIM = DATA / "interim"   # parsed-but-not-final intermediates (gitignored)
DATA_PROCESSED = DATA / "processed"  # the analysis panel (gitignored)

PAPER = REPO_ROOT / "paper"
FIGURES = PAPER / "figures"
TABLES = PAPER / "tables"

for _p in (DATA_RAW, DATA_INTERIM, DATA_PROCESSED, FIGURES, TABLES):
    _p.mkdir(parents=True, exist_ok=True)
