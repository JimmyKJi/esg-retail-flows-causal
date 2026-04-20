# Notebooks

Run in numerical order. Each notebook writes its outputs to `/data/processed` or `/results`, which the next notebook reads.

| Notebook | Purpose | Input | Output |
|---|---|---|---|
| `01_data_ingestion.ipynb` | Pull raw data from Yahoo Finance, SEC EDGAR, Fama-French library. | External APIs | `data/raw/*.parquet` |
| `02_panel_construction.ipynb` | Assemble firm-quarter panel with ESG scores, holdings, controls. | `data/raw/` | `data/processed/firm_quarter_panel.parquet` |
| `03_event_study.ipynb` | Stacked DiD around rating-change events. | `data/processed/` | `results/tables/event_study.csv`, event-study figure |
| `04_instrumental_vars.ipynb` | IV using ESG-index inclusion + reverse-causality test + placebos. | `data/processed/` | `results/tables/iv_results.csv` |
| `05_results.ipynb` | Final tables and figures for the write-up. | All prior outputs | `results/figures/*.png`, final report markdown |

Every cell is idempotent: running a notebook twice produces identical outputs, assuming the upstream inputs have not changed. Random seeds are fixed at the top of each notebook.
