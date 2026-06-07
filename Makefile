# ESG Label or Just the Index? — reproducible pipeline
#
# Raw and interim data are gitignored; every target rebuilds from source.
# Provenance for each input lives in data/DATA_LINEAGE.md. The SEC-hosted
# targets (data-sec) require an unblocked network — see the SEC access note in
# README.md. Phase 2-5 targets are intentionally gated: they fail loudly until
# their upstream data (13F + N-PORT) has landed. That is by design, not a bug —
# replace the gate with the real driver when you implement that phase.

PY     := ./venv/bin/python
PYTEST := ./venv/bin/pytest

.DEFAULT_GOAL := help
.PHONY: help data data-sec panel matched car estimate placebo robustness heterogeneity credibility figures test clean

help:  ## Show this help
	@echo "ESG flows — pipeline targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

# ── Phase 1: data ingestion ──────────────────────────────────────────────────

data:  ## Pull reachable sources: Fama-French, S&P 500 placebo, prices (works anywhere)
	$(PY) -m src.ingest.ff_factors
	$(PY) -m src.ingest.sp500_events
	$(PY) -m src.ingest.prices

data-sec:  ## Pull SEC sources: 13F outcome + N-PORT treatment (REQUIRES an unblocked network)
	@echo ">> Set SEC_EDGAR_UA in .env first (see README). Fails with EdgarBlocked on a filtered IP."
	$(PY) -m src.ingest.edgar_13f
	$(PY) -c "from src.ingest.nport_holdings import build_inclusion_events; build_inclusion_events(refresh=True)"

# ── Phases 2-5: build + estimate (gated on data-sec) ─────────────────────────
# Not yet runnable: each needs the 13F/N-PORT panels that data-sec produces.
# These recipes stop the build with a clear pointer rather than failing deep in
# Python with a missing-argument error.

panel:  ## Phase 2 — build the firm x quarter panel + S&P 500 placebo arm (needs interim 13F + N-PORT)
	@test -f data/interim/holdings_13f.parquet -a -f data/interim/esg_inclusion_events.parquet \
	  || { echo "Missing interim 13F/N-PORT parquets — run 'make data-sec' from an unblocked network first."; exit 1; }
	$(PY) -m src.build.panel

matched:  ## Phase 2b — matched controls (PSM + CEM) for the ESG and placebo arms (needs panel)
	@test -f data/processed/panel.parquet \
	  || { echo "Missing data/processed/panel.parquet — run 'make panel' first."; exit 1; }
	$(PY) -m src.build.matching

car:  ## Phase 2b — FF-adjusted CAR secondary outcome on the S&P 500 placebo arm (needs network)
	@test -f data/interim/sp500_events.parquet -a -f data/interim/ff_factors_daily.parquet \
	  || { echo "Missing S&P 500 events / FF factors — run 'make data' first."; exit 1; }
	$(PY) -m src.build.car

estimate:  ## Phase 3 — event study + heterogeneity-robust staggered DiD (needs panel + matched)
	@test -f data/processed/panel.parquet \
	  || { echo "Missing data/processed/panel.parquet — run 'make panel' first."; exit 1; }
	@test -f data/processed/matched_esg_cem.parquet \
	  || { echo "Missing matched controls — run 'make matched' first."; exit 1; }
	$(PY) -m src.estimate.did

placebo:  ## ESG vs S&P 500 placebo contrast (H2; produced by 'make estimate')
	@echo ">> H2 placebo contrast is produced by 'make estimate' -> results/h2_esg_specific.csv"
	@test -f results/h2_esg_specific.csv || { echo "Not found — run 'make estimate' first."; exit 1; }

robustness:  ## Phase 4 — pre-registered robustness battery (needs panel + matched)
	@test -f data/processed/panel.parquet -a -f data/processed/matched_esg_cem.parquet \
	  || { echo "Missing panel/matched controls — run 'make panel matched' first."; exit 1; }
	$(PY) -m src.estimate.robustness

heterogeneity:  ## Phase 5 — H4 filer-type re-ingest + ESG/passive contrast (needs raw 13F bundles + panel + matched)
	@ls data/raw/edgar_13f/*.zip >/dev/null 2>&1 \
	  || { echo "Missing cached 13F bundles — run 'make data-sec' from an unblocked network first."; exit 1; }
	@test -f data/processed/panel.parquet -a -f data/processed/matched_esg_cem.parquet \
	  || { echo "Missing panel/matched controls — run 'make panel matched' first."; exit 1; }
	$(PY) -m src.ingest.edgar_13f_byfiler
	$(PY) -m src.estimate.h4_filer

credibility:  ## Phase 6 — credibility of the null: power/MDE + equivalence + honest DiD + placebo-in-time (needs estimate)
	@test -f results/h2_esg_specific.csv -a -f results/event_studies.parquet -a -f results/summary.csv \
	  || { echo "Missing estimation output — run 'make estimate' first."; exit 1; }
	@test -f data/processed/panel.parquet \
	  || { echo "Missing data/processed/panel.parquet — run 'make panel' first."; exit 1; }
	$(PY) -m src.estimate.credibility

figures:  ## Build paper figures + tables from estimation output (needs estimate)
	@test -f results/event_studies.parquet \
	  || { echo "Missing results/event_studies.parquet — run 'make estimate' first."; exit 1; }
	$(PY) -m src.viz.figures

# ── Quality ──────────────────────────────────────────────────────────────────

test:  ## Run the suite: reachable-data smoke + SEC-transform unit tests
	$(PYTEST) -q

clean:  ## Remove Python/pytest caches (leaves data/ and results/ untouched)
	rm -rf .pytest_cache
	find . -path ./venv -prune -o -name __pycache__ -type d -exec rm -rf {} +
