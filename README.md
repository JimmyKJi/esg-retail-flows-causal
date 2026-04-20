# ESG Ratings and Capital Flows: A Causal Inference Study
 
**Research question:** Do ESG rating upgrades *cause* institutional capital inflows, or do prior inflows cause ESG rating upgrades?
 
**Hypothesis:** The causal direction runs from flows to ratings, not ratings to flows. Rating agencies appear to follow capital allocation patterns rather than lead them.
 
**Method at a glance:** Panel event-study difference-in-differences around ESG rating changes, with stock-level fixed effects. Instrumental-variables robustness check using ESG index inclusion as an exogenous shock. Placebo tests on non-ESG index reshuffles.
 
**Stack:** Python, Pandas, DoWhy, CausalML, statsmodels, linearmodels.
 
**Status:** In development. Target completion: Q3 2026.
 
---
 
## Why this question
 
Between 2018 and 2024, global ESG-labelled assets under management grew from roughly $1 trillion to over $3 trillion before plateauing during the 2023–2024 ESG backlash. Industry narrative treats ESG ratings as a *driver* of capital allocation: companies rated higher on E, S, and G dimensions are said to attract flows from mandated sustainable funds.
 
But the reverse causal story is equally plausible. Rating agencies are not independent observers — they have commercial incentives to align their ratings with what capital is already doing, because disagreement with market consensus is costly (customer churn, reputational risk, methodology pressure). If that is the dominant dynamic, then ESG ratings are less an informational input to the market and more a trailing indicator of it.
 
This question matters because regulators (SEC climate disclosure rule, EU SFDR, UK SDR) are increasingly treating ESG ratings as quasi-authoritative signals. If ratings are actually endogenous to capital flows, much of the regulatory architecture built around them rests on a reversed causal assumption.
 
## Research design
 
The unit of analysis is the firm-quarter. The panel covers US-listed equities from 2018 Q1 to 2024 Q4.
 
### Treatment
 
An ESG rating *change* event: a material upgrade or downgrade by a major rating provider (MSCI ESG, Sustainalytics, Refinitiv ESG). Rating-change dates are used as the event windows.
 
### Outcome
 
Two flow outcomes are tracked post-event:
 
1. **Institutional ownership share** (from SEC 13F filings, aggregated quarterly).
2. **ETF flows** into the firm's stock, computed from ETF holdings data plus fund-level daily flows.
### Identification strategy
 
Three approaches are stacked for triangulation:
 
1. **Stacked difference-in-differences** (Cengiz et al. 2019): each rating-change event creates a treatment cohort; matched control firms are drawn from firms with similar pre-event ESG scores and industry/size profiles. Event-time coefficients are estimated with stock and calendar-time fixed effects.
2. **Instrumental variables**: inclusion in or removal from major ESG indices (MSCI ESG Leaders, S&P 500 ESG) is used as an instrument for rating changes. Index decisions follow mechanical rule-based methodologies and are plausibly exogenous to firm-level flow dynamics.
3. **Placebo tests**: non-ESG index reshuffles (e.g. Russell 1000 rebalancing) should show no effect on ESG-related capital flows; significant placebo effects would invalidate the design.
### What rules out reverse causality
 
The paper explicitly tests the reverse direction: do *lagged* capital flows predict *future* rating changes? If both directions show statistically significant effects, the finding is that the causal system is bidirectional. If only one direction does, the identification closes cleanly.
 
## Data sources
 
| Source | Data | Cost | Coverage |
|---|---|---|---|
| Yahoo Finance | Daily prices, volumes, sustainability scores | Free | US listed equities |
| SEC EDGAR | 13F institutional holdings filings | Free | Quarterly since 2013 |
| Kenneth French Data Library | Fama-French factor returns for control | Free | 1926 – present |
| MSCI ESG Ratings | Firm-level ESG scores | Free (historical snapshots via academic mirrors) | 2018 – 2023 |
| CRSP / Compustat | Higher-quality returns and fundamentals | Subscription (KCL library) | 1925 – present |
| ETF.com / morningstar | ETF holdings and flows | Free (rate-limited) | Since 2010 |
 
All raw data is held in `/data/raw` (git-ignored). Processed panels are held in `/data/processed`.
 
## Repository structure
 
```
esg-retail-flows-causal/
├── README.md                    This document
├── requirements.txt             Python dependencies
├── .gitignore
├── data/
│   ├── raw/                     Raw pulls (git-ignored)
│   └── processed/               Cleaned panels ready for analysis
├── notebooks/
│   ├── 01_data_ingestion.ipynb  Raw data pulls and validation
│   ├── 02_panel_construction.ipynb   Firm-quarter panel assembly
│   ├── 03_event_study.ipynb     Stacked DiD estimation
│   ├── 04_instrumental_vars.ipynb    IV robustness
│   └── 05_results.ipynb         Tables and figures for write-up
├── src/
│   ├── data_loader.py           API wrappers and raw-data retrieval
│   ├── panel_builder.py         Panel construction and cleaning
│   ├── causal_models.py         DoWhy and linearmodels estimation
│   ├── event_study.py           Stacked DiD implementation
│   └── viz.py                   Plotting helpers
├── results/
│   ├── figures/                 Output charts
│   └── tables/                  LaTeX / markdown result tables
└── LICENSE
```
 
## Reproducibility
 
Running the full pipeline end-to-end:
 
```bash
git clone https://github.com/JimmyKJi/esg-retail-flows-causal.git
cd esg-retail-flows-causal
python -m venv venv
source venv/bin/activate    # or venv\Scripts\activate on Windows
pip install -r requirements.txt
jupyter lab
```
 
Run notebooks in order 01 through 05. Total runtime on a standard laptop: approximately 2 hours end-to-end, bottlenecked by SEC EDGAR download throttling.
 
Random seeds are fixed throughout. Results should reproduce exactly.
 
## Planned milestones
 
- **Weeks 1–2:** Data ingestion pipeline, panel construction validated.
- **Weeks 3–4:** Event study baseline results.
- **Weeks 5–6:** IV robustness and placebo tests.
- **Weeks 7–8:** Write-up, figures, and public release of findings.
## About
 
Built by Jimmy Kaian Ji. KCL Philosophy BA (Y1, 2026). Interested in applying causal-inference methodology to problems in corporate strategy, capital markets, and regulatory design.
 
Related work: [HR Attrition Analytics Project](https://github.com/JimmyKJi/hr-attrition-analytics) — an earlier Python project using logistic regression and policy simulation to model employee attrition risk.
 
Contact: LinkedIn at [linkedin.com/in/jimmy-kaian-ji](https://www.linkedin.com/in/jimmy-kaian-ji/).
 
---
 
*This repository represents original analysis. All findings will be reported honestly regardless of whether they support the initial hypothesis.*
