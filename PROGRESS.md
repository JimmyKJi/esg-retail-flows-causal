# PROGRESS

Running log, newest first. One entry per working session.

## 2026-06-07 (cont. 7) — V2 SCOPING: DECOMPOSED THE BOTTLENECK BEFORE SPENDING EFFORT

**Scoped v2 against the *realised* panel before committing any work — and found the
cont. 6 "widen both arms" roadmap was partly wrong. The two open dimensions need
*different* fixes, and the obvious "add more ETFs / a longer panel" move barely helps
the one that matters (H3, the novel decay hook). Corrected paper §5.3 + §7, the README
Roadmap, and the stale "~3 post-2022 quarters" power excuse. Docs-only; no results
re-run; 56 tests still apply.**

**1. The decomposition (read straight off `panel.parquet`).** ESG arm = **334**
events (split at 2022Q1: **189** late / **145** early). S&P 500 placebo = **123** raw
adds → **65** clean (58 are *also* ESG names, dropped to keep the placebo non-ESG) —
that 65 is what sets H2's se ≈ 37.3. H3's se = hypot(se_early 10.06, se_late 15.03) =
**18.09**; the late half is noisier *despite* more firms, because its most recent
cohorts have truncated 0–4 post-windows.

**2. H2 bottleneck = cheap but low-value.** H2's precision is the 65-event placebo
arm. Extending the panel **backward** is cheap (13F structured filings exist from
2013; S&P 500 change history is free) and would roughly double that arm — but H2 is
*already* well-powered, so the marginal value is low.

**3. H3 bottleneck = structural, and ESG-arm only.** `decay_split` (did.py:383) runs
on the ESG arm alone — it splits the 334 ESG events and differences the halves — so a
larger *placebo* arm does **nothing** for H3. Its real constraints are structural: the
ETF/N-PORT holdings proxy **cannot reach before 2019Q1** (N-PORT public data begins
April 2019 — [SEC press release 2017-226](https://www.sec.gov/newsroom/press-releases/2017-226)),
and MSCI USA ESG Leaders is a single index with a roughly fixed constituent count, so
adding ESG ETFs surfaces few new names.

**4. The only real unlock for H3 = a licensed non-ETF membership history.** A
**MSCI ESG Leaders constituent *history*** (subscription — MSCI, Bloomberg, or
Refinitiv) is the single move that both extends the ESG arm back to the index's ~2016
launch *and* removes the CUSIP-churn measurement error of inferring membership from an
ETF-holdings diff. Supersedes the cont. 6 §4 generic "widen both arms" roadmap, which
conflated H2's (cheap, low-value) fix with H3's (structural, licence-gated) one.

### Next
- The one decision that is the user's: whether to license a non-ETF membership feed.
  It is the *only* route to move H3 from *inconclusive* to *answered*; everything else
  (more ETFs, longer panel) leaves H3 where it is.
- Absent that, the repo is submission-ready as-is: a well-powered, honestly-scoped
  **breadth** null with a transparent credibility battery; depth + decay left open.

## 2026-06-07 (cont. 6) — VIVA-PROOFING: AUDIT + DUAL-AUDIENCE README + CLAIM-SCOPING

**Hardened the briefs against a sharp reviewer. (i) Full statistical audit:
reconciled every hand-typed number to `results/` — Tables 1/2/3, all H2/H3/H4 +
robustness + credibility figures, event-study peaks, δ=183, placebo p-values, and
the 56-test count all tie out exactly; two errors found and fixed — an MDE↔SESOI
conflation ("a quarter the size of a generic add ≈104 filers" wrongly merged the
80%-power MDE with the 0.25× equivalence benchmark) and an M\* rounding slip
(0.27→0.26, true value 0.2648). (ii) Rewrote the README for two audiences:
plain-first headline, a collapsible plain-language primer, a table reader's guide,
and plain hooks on the dense rows — method names and exact numbers preserved. (iii)
On pointed feedback, scoped the claim precisely everywhere: the defensible,
well-powered result is *breadth only* (count of 13F filers); *depth* (MDE 1.26,
equivalence FALSE) and the H3 *decay* split (MDE ≈51 ≫ |Δ|=12) are now labelled
**inconclusive (underpowered), not null** — never "no effect." Every version now
leads with the equivalence/power bound and demotes the −121 point estimate to a
pre-trend-fragile footnote (M\*≈0.26) we don't lean on. Named the data soft
underbelly loudly (ETF-holdings *proxy* + 65-event placebo arm = the precision
bottleneck behind se 37.3) and added a v2 roadmap. Docs-only; 56 tests green;
committed + pushed.**

**1. Audit — ground truth vs hand-typed.** Dumped every result CSV/parquet and
checked each prose/table number against it. Only two issues (both fixed in
README/PROGRESS/DATA_LINEAGE + abstract/conclusion); §5.2 caption "+33/+290"
verified *correct* (describes the CS-matched solid line, not the Sun-Abraham peaks)
and left untouched — did not "fix" a right number.

**2. Dual-audience README.** Plain-language story up top (the ESG label draws no
extra *investors*; it's just the generic index-add effect), then the precise
version; `<details>` primer glossing 13F filers / breadth / depth / the S&P-500
placebo / parallel-trends / the well-powered "honest null"; estimator footnote
glossed in plain terms.

**3. Claim-scoping (the substantive fix).** Corrected two genuine over-claims that
contradicted the credibility table: §1 "depth ... is a precise zero" and §5.2 "H2
not supported on *either* outcome" → depth is the ESG *arm's* tight zero but the
ESG-*specific* depth contrast is *inconclusive/underpowered*. Retitled verdicts
(H2 depth, H3 breadth/depth) from "not supported" to "inconclusive — underpowered."
Abstract, §1 Findings, §5.3, §5.5 table, §8 conclusion all rescoped to breadth +
"could not detect decay" framing. README headline, results table, why-rigorous #2,
estimator footnote, guardrails, and figure caption rescoped to match.

**4. v2 roadmap.** New `## Roadmap (v2)` in README + a "natural next version"
paragraph in paper §7: power up H3 (legitimacy decay) with (i) more inclusion
events (longer panel / more ESG ETFs → both arms wider) and (ii) a cleaner non-ETF
index-membership source (MSCI constituent list / licensed feed) for exact treatment
timing. Would sharpen the placebo arm's precision; would *not* overturn the breadth
null. [cont. 7 correction: "→ both arms wider" was wrong — H3 is ESG-arm only, so a
bigger placebo arm does nothing for it. H2's fix (extend panel backward) is cheap but
low-value; H3's fix (licensed non-ETF membership history) is the only one that moves
the decay test. See cont. 7.]

### Next
- v2 is the real extension if revisited: source a non-ETF index-membership feed +
  widen the event count to move H3 from *inconclusive* to *answered*. Data-access
  dependent (MSCI licensing / longer panel), so not started — documented as roadmap.
- Otherwise the repo is submission-ready: well-powered, honestly-scoped breadth null
  with a transparent credibility battery.

## 2026-06-07 (cont. 5) — PHASE 6: CREDIBILITY OF THE NULL (power, honest DiD, randomization)

**Turned "we found nothing" into a bounded, defensible claim. A pre-specified
three-part credibility battery shows the ESG-specific *breadth* null is genuine
evidence of absence — the design's minimum detectable effect at 80% power is ≈104
filers, and the 95% CI rules out a positive premium even a quarter the size of a
generic add — while *depth* and the H3 *decay* split are reported, honestly, as
underpowered. An
honest-DiD sensitivity analysis (Rambachan-Roth 2023) makes the most candid point
in the paper: the *significantly negative* breadth point estimate is itself
pre-trend-fragile (breakdown M\* ≈ 0.26 against the matched controls' large δ=183),
so the conclusion rests on power, not on the negative sign. Placebo-in-time
randomization confirms the +28-filer breadth level isn't a timing artifact
(p=0.013). 56 tests green (+6 this session). Committed + pushed.**

**1. Module — `src/estimate/credibility.py` (low-risk by design).** Pieces A
(power/MDE/equivalence) and B (relative-magnitudes/honest DiD) are **pure,
deterministic post-processing** of the frozen result CSVs/parquet — no
re-estimation, so they can't perturb the headline. Only piece C (placebo-in-time)
re-fits, isolated to a seeded run (`seed=12345`, 300 draws/outcome) on the
treated∪matched-control sub-panel for speed. SESOI pre-set at ¼ of the mechanical
inclusion effect; M-grid {0..2}; the honest-DiD bound is the conservative additive
worst-case (point ± 1.96·se ± M·δ), deliberately looser than the exact ARP set.

**2. Findings, reported either way.** A: breadth `rules_out_meaningful=True`
(CI [−194.5, −48.5], all below the +37.3 SESOI); the two ESG-*named* H4 channels
also rule out a meaningful effect; depth/passive/H3 are `False` (underpowered,
stated). B: contrast breakdown M\*≈0.265, ESG-arm M\*≈0.238 — the negative sign
breaks under a small post-trend violation, so it is *not* relied on; depth breaks at
M\*=0 (already non-sig). C: breadth real +27.6 vs placebo mean +1.6 (sd 11.0),
p=0.013; depth real ≈0 vs placebo, p=0.97.

**3. Exhibits + wiring.** Added 3-panel `credibility_plot()` (power on an SE-axis,
green=precise null; honest-DiD robust-CI fan with the M\* line; placebo histogram)
→ `paper/figures/credibility.png`; 3 markdown tables via `write_tables()`. Wired
`credibility_plot()` into `figures.main()` (guarded) and added a `make credibility`
target (.PHONY + guards on the estimate outputs + panel). 6 unit tests pin the
closed-form MDE/CI, the precise-vs-underpowered verdicts, the robust-bounds grid,
and the breakdown-M edge cases to the frozen numbers.

**4. Docs.** New paper §5.7 "Credibility of the null" (power/equivalence Table 3 +
honest-DiD + placebo, with the "rests on power, not the sign" framing and the
conservative-bound caveat); abstract + conclusion now carry the bounded-null claim;
added the Rambachan-Roth reference. README results-at-a-glance Credibility row +
status (Phase 6) + 56 tests + repo listing + reproduce steps; DATA_LINEAGE Phase-6
section.

### Next
- Phase 6 closes the analytical arc (identification → robustness → heterogeneity →
  credibility). Remaining is presentation: optional 1-page non-technical abstract
  (PDF) for the application packet.
- The normative framing (hook 4: SFDR/SDR/SEC) could still be expanded into a
  standalone policy section if a reviewer wants it.

## 2026-06-07 (cont. 4) — PHASE 5: H4 FILER-TYPE HETEROGENEITY (the real shot at the null)

**The null survives the one analysis that could legitimately have broken it. We
re-ingested the raw 13F at the manager (CIK) grain and decomposed the response by
filer type — but the ESG-specific contrast (ATT_ESG − ATT_S&P) is *negative* for
all four filer-type outcomes (0/4 supported). Neither ESG-named managers nor
passive index-trackers — not even passive *depth*, the mechanical channel — pile
into ESG adds more than into generic S&P adds. The flat aggregate is not hiding a
composition shift. The one contrast whose ESG pre-trends pass (`log_shares_esg`)
is significantly negative (−1.13, p=0.026). 50 tests green (+3 this session).**

**1. Re-ingest, no network — `src/ingest/edgar_13f_byfiler.py`.** The frozen panel
is cusip×quarter, so to recover filer identity I re-parse the already-cached raw
13F bundles (`data/raw/edgar_13f/*.zip`, 2.0 GB, no SEC calls) at the CIK grain,
classify each manager name with the pre-committed `heterogeneity.py` heuristics,
and write per-type breadth (distinct typed filers) + depth (shares) columns over
the 1,507-CUSIP analysis universe. Breadth dedups to one row per (cusip, CIK)
before the boolean-sum so amendments / multi-share-class rows can't inflate it.
**Reconciles exactly** against the frozen breadth measure: max |Δ| = 0 across all
38,088 (cusip, period) rows.

**2. Estimation — `src/estimate/h4_filer.py`.** Merges the type columns onto the
panel on (cusip, q_idx), 0-fills genuine absences, derives `log_shares_*`, and runs
the **identical** matched Sun-Abraham ESG-vs-S&P contrast (`did.esg_specific_contrast`)
per outcome — so H4 inherits the exact decision rule (positive, p<.05, ESG
pre-trend passes). Writes `results/h4_filer.csv`. 0/4 supported.

**3. The honest read.** att_esg is small-positive everywhere (+0.10 to +0.20) but
att_sp500 is *larger* every time, so the contrast is negative. Economic logic
(consistent with H2): an S&P 500 add is a bigger real event (large-cap graduation
every manager buys); ESG-index inclusion is a label on a name funds already hold.
Key measurement caveat, stated everywhere: 13F is filed at the *manager* level, so
`*_esg` captures ESG-*branded* boutiques only — the BlackRock/Vanguard ESG-sleeve
channel surfaces as **passive depth**, which we tested directly and which is also
negative. This bulletproofs the null against "you measured the wrong outcome."

**4. Exhibits + docs.** Added `h4_filer_plot()` (forest plot, breadth/depth facets,
red = not supported, manager-level caveat in caption) → `paper/figures/h4_filer.png`
and `paper/tables/h4_filer.md`. Rewrote paper §5.4 from "not estimable" to a full
results subsection + table; updated the abstract, decision rule, README "Results at
a glance" H4 row + heterogeneity caveat + status (Phase 5), and DATA_LINEAGE with a
Phase-5 section. Retired the now-false `results/H4_NOT_ESTIMABLE.txt` (git rm) and
updated `did.py`/`heterogeneity.py` notes to point at the new pipeline. Added the
`make heterogeneity` target.

### Next
- Phase 5 is the last analytical hook. Remaining is presentation: optional 1-page
  non-technical abstract (PDF) for the application packet.
- The normative framing (hook 4: SFDR/SDR/SEC) lives in the paper intro/conclusion;
  could be expanded into a standalone section if a reviewer wants the policy angle.

## 2026-06-06 (cont. 3) — PHASE 4: PRE-REGISTERED ROBUSTNESS BATTERY

**The headline null survives the full pre-registered robustness battery. The H2
ESG-specific breadth contrast (ATT_ESG − ATT_S&P) is negative in all 8
specifications and significant in all 7 that carry inference (−61 to −137 filers);
depth is negative in all 8 and significant in none. The sign never flips across
matching scheme, averaging horizon, outlier treatment, COVID exclusion, or
treatment definition. 47 tests green (+7 this session).**

**1. New module — `src/estimate/robustness.py`.** Reuses the frozen `did.py`
estimators (no edits to the Phase-3 module). For each primary outcome it sweeps:
baseline (CEM, post 0..4); alt horizons 0..2 / 0..6 (recomputed from the same SA
fit's delta-method covariance via `_window_att`); PSM-matched controls; winsorise
the level outcome 1/99; exclude COVID 2020Q1–Q2 (q_idx 8081/8082); drop the 177
`ever_dropped` ESG firms; and the full clean-control pool via Callaway-Sant'Anna
point estimate (SA infeasible on ~95k controls). Writes `results/robustness.csv`
(16 rows) + `results/robustness_notes.txt`.

**2. Sanity-pinned to the frozen results.** The baseline row reproduces
`h2_esg_specific.csv` exactly (n_filers −121.468; log_shares −0.400), and a unit
test asserts `_window_att(res, POST_WINDOW)` equals the estimator's own
`post_att`/`post_se` — so the recompute can't silently drift.

**3. Two variants honestly recorded as NOT estimable** (not faked): SA on the full
pool (dense saturated design → CS point estimate), and treatment-definition (b)
"restrict post to before first exit" (panel has `ever_dropped` but no per-firm exit
quarter). Both in `results/robustness_notes.txt`.

**4. Paper updated.** Added §5.6 Robustness + Table 2; converted limitation #8 from
"battery partially run / next step" into "complete except two recorded exceptions";
strengthened the conclusion to cite the battery. Also fixed the stale econ-stack
README note (the pyfixest/differences stack runs in this venv).

**5. Nuance worth noting.** Winsorising at 1/99 roughly halves *both* arms' breadth
effects (ESG +27.6→+12.2, S&P +149→+73.4) — so the largest firms carry much of the
generic-add breadth — but the ESG-specific contrast stays significantly negative
(−61.3, p=0.015). The ordering ESG ≤ generic is not an outlier artefact.

**6. Admissions polish (done).** README now leads with the `esg_vs_placebo.png`
money shot inline and a hypothesis→verdict "Results at a glance" table (H1–H4 +
robustness), so a reviewer sees question → picture → null in the first screen.
Status bumped to Phase 4; module listing, test count (47), and data/reproduce
notes refreshed. Committed `aaa858d` (battery) + `e6f9499` (polish), both pushed.

### Next
- H4 only becomes estimable by re-ingesting raw 13F INFOTABLE keyed by CIK.
- Optional: 1-page non-technical abstract (PDF) for the application packet.

## 2026-06-06 (cont. 2) — RESEARCH NOTE WRITTEN + FULL ACCURACY AUDIT

**The paper is drafted (`paper/paper.md`) and the whole repo has been swept for
inaccuracies. An independent audit confirmed every reported number is accurate to
rounding and found no bias-inducing bug in the build/estimation layer; the defects
were documentation-level (false "unit-tested" claims, a stale matcher docstring,
and three count reconciliations) and are now fixed. 40 tests still green.**

**1. Paper.** `paper/paper.md` — full research note: intro, institutional setting +
H1–H4, data, empirical strategy, results (H1/H2/H3/H4), normative discussion,
8-item limitations, conclusion, 11 references. Embeds the 3 figures + Table 1
(windowed post-ATT by outcome/arm) and the H2/H3 verdict table. All numbers sourced
from `results/*.csv`.

**2. Independent audit (subagent, build-layer + paper numbers + cross-doc).**
Confirmed: 2023 13F VALUE ×1000 units correct; event-time alignment correct;
matching baseline at g−1 (no look-ahead); CAR window no leakage; pre-trends Wald
correct; contrast SEs (independent-arm `np.hypot`) documented. **No estimation bug.**

**3. Inaccuracies fixed (the "rid of bugs" pass).**
- Removed two false **"unit-tested"** claims: the H4 classifier (`paper.md` §5.4,
  `PROGRESS` H4 section) and the crosswalk (`DATA_LINEAGE` source row) — these are
  *implemented/validated*, not unit-tested (no `test_crosswalk.py`/heterogeneity test).
- `crosswalk.py` module docstring rewritten: it described a *conservative
  unique-subset* fallback, but the code does a **prominence tie-break** (highest
  13F-row support wins) — now matches the function docstring + behaviour.
- Table 1 footnote added clarifying Callaway-Sant'Anna returns **no** pre-trend, so
  the pre-trend columns are companion tests (TWFE on the full pool; Sun-Abraham on
  the matched pool).
- README "Heterogeneity" point flagged as coded-but-not-estimable.

**4. Count reconciliations (verified against the local parquet, then documented).**
- **124 → 123:** the 124 matched S&P add-*events* collapse to 123 unique CUSIPs —
  one issuer (CUSIP 35137L105) was S&P-added twice in-window. Matched-CUSIP set ==
  panel placebo-treated set exactly (0 diff both directions).
- **101 vs 65:** matching ran on 101/123 placebo firms (22 lack a baseline g−1),
  *including* the 58 `both_treated`; the headline H2 contrast keeps only the 65
  clean-generic (`both_treated` excluded) = `n_treated` in `summary.csv`. ESG matched
  332/334 (2 lack a baseline g−1). All written into `DATA_LINEAGE`.
- **CAR coverage:** 124 add-events = 99 ok + 20 insufficient-pre + 3 no-prices +
  2 date-edge (was mis-stated as "99/20/3").

**5. New committed artifact.** `results/car_summary.csv` — the [−5,+5] CAR headline
(n=99, +1.35%, t=1.55, 54% positive) + full status breakdown, so the paper's CAR
numbers are reproducible from a tracked file (the parquet is gitignored).

### Next
- Robustness battery (PSM↔CEM↔full, ±3/±6 windows, winsorise, drop COVID quarters,
  drop `ever_dropped`) needs the conda econ stack — run on an analysis machine.
- H4 only becomes estimable by re-ingesting raw 13F INFOTABLE keyed by CIK.

## 2026-06-06 (cont.) — PHASE 3 ESTIMATION: STAGGERED DiD + EVENT STUDY (task #10 / Phase 3 done)

**The headline is a clean null, honestly reported: the apparent "ESG inclusion →
flows" effect is the *mechanical index-inclusion* effect, not an ESG-label effect
— and a generic S&P 500 addition pulls in ~5× more institutional breadth than an
ESG-Leaders addition. On the credible matched design the ESG pre-trends fail, so
even H1 is not a clean causal estimate; we say so plainly per the pre-registration
decision rule. 40 tests green (+13 this session).**

**1. What ran (`src/estimate/did.py`, the frozen Phase-3 battery).** Three
estimators × two control pools × two arms × three outcomes, all on *levels*
(each differences internally vs the reference period e=−1):
- **Callaway-Sant'Anna (2021)** group-time ATT(g,t) via `differences`, aggregated
  to a dynamic event study — HEADLINE.
- **Sun-Abraham (2021)** interaction-weighted event study, built *manually* (no
  `sunab` exists in `pyfixest`): a saturated cohort×event-time regression, then a
  cohort-share-weighted aggregation matrix `A` with a delta-method covariance
  `A V Aᵀ` that carries the windowed post-ATT and the pre-trends Wald test —
  HEADLINE cross-check, and the estimator H2/H3 use.
- **naive TWFE** `i(event_time, ref=−1)` — Goodman-Bacon baseline, *not* headline.
- **Pools:** `full` (all ~95k clean controls, the pre-registered comparison) and
  `matched_cem` (Phase-2b size/ownership match, the credible comparison).
- Arms: ESG (334 treated) and the S&P 500 placebo (65 clean S&P-only adds; the 58
  both-treated firms excluded). Matched controls: ESG 569, S&P 370.

**2. H1 (inclusion → flows) — NOT cleanly supported; pre-trends are the binding
constraint.** Matched-CEM Sun-Abraham breadth = **+27.6 filers (se 9.4)** post,
but the joint pre-trends Wald **FAILS (p=0.001)**; depth (log_shares) is a precise
**≈0 (−0.004, se 0.085, ns)**. The full-pool estimate is larger (**+79.7** filers)
and *more* confounded (pre-trend p≈1.6e-24) — the full pool is micro-caps on a
steep secular ownership uptrend, exactly the population mismatch Phase 2b
flagged. Matching balances the *level* at e=−1 but not the *trend* (selection-
into-index growth), so the pre-trend survives. This is the load-bearing failure
the pre-registration anticipated; per its decision rule we report the
heterogeneity-robust point estimates **with the pre-trend caveat attached**, not
as causal. *Telling detail:* the one ESG spec whose pre-trends **PASS** is
log_value (p=0.488) — and there the effect is a precise **zero** (−0.082, ns),
which only reinforces the no-ESG-effect read.

**3. H2 (ESG-specific = ATT_ESG − ATT_S&P) — NOT supported, and informatively so.**
Windowed post-ATT, matched SA, breadth: **ESG +27.6 vs S&P +149.0 →
ESG-specific = −121.5 (se 37.3, p=0.001)**. The contrast is large, significant,
and **negative**: the ESG label attracts *less* institutional breadth than a
plain index addition. log_shares: −0.40 (p=0.373), also not supported. The
"ESG flow premium" is not ESG-specific — it is (a fraction of) the mechanical
S&P-inclusion effect. The `esg_vs_placebo.png` y-axes (ESG tops ~+33, S&P ~+290)
make the asymmetry visible at a glance.

**4. H3 (legitimacy decay, cohorts split at 2022Q1) — directional but
underpowered.** late−early windowed post-ATT is **−12.1 filers (p=0.504)** and
**−0.13 log_shares (p=0.421)** — both *signed* the decay way, neither significant.
Underpowered by construction (splitting the ESG arm in two + differencing inflates
the SE to 18.1); reported as inconclusive, direction noted. [cont. 6 correction: the
earlier "~3 post-2022 quarters of data" reason was inaccurate — the panel runs to
2026Q1 with 189 late vs 145 early ESG firms; the limit is variance, not data span.]

**5. H4 (passive/active, ESG-badged heterogeneity) — NOT estimable.** The 13F
outcome was cached as cusip×quarter aggregates, so per-filer manager (CIK)
identity is gone. The *classification* methodology is implemented
(`classify_passive`, `classify_esg_filers`); `split_passive_active` raises the
canonical data-limitation note. Recorded honestly (`results/H4_NOT_ESTIMABLE.txt`).

**6. Correctness fix shipped — IW aggregation normalization.** When `pyfixest`
drops a collinear cohort×event cell (e.g. `d_g8090_ep2`, which sits in the
post-window), the Sun-Abraham cohort-share weights must normalise over the
**surviving** cells only; dividing by the full cohort count would put weight on a
dropped cell and bias att(e) toward 0. Verified the fix perturbs *only* fits with
a dropped post-window cell (S&P breadth +148.4→+149.0; ESG breadth unchanged at
+27.6, no post-window drop). Also fixed a formula-parser bug — literal `-` in
dummy names is read as subtraction by `formulaic`, so event-time signs are encoded
`m`/`p` (`d_g8090_em3` / `_ep2`) via the new `_sa_cell` helper — and a
DataFrame-fragmentation slowdown (build dummies in one `concat` block).

**7. Deliverables + wiring.** `results/{event_studies.parquet, summary.csv,
h2_esg_specific.csv, h3_decay.csv, H4_NOT_ESTIMABLE.txt}` (committed; raw/interim
stay gitignored); `paper/figures/{event_study,esg_vs_placebo,decay}.png` and
`paper/tables/{summary,h2_esg_specific,h3_decay}.md` from `src/viz/figures.py`
(reads saved results, never re-fits). `make estimate` and `make figures` now run
the real drivers (were gated stubs); the four estimator scaffolds
(`event_study/placebo/structural_break/heterogeneity.py`) are honest thin wrappers
over `did.py`. `DATA_LINEAGE.md` updated for the Phase-3 outputs.

### Next
1. **Phase 5 — the writeup.** Draft the short paper around the honest result:
   index-inclusion mechanics dominate; no ESG-specific flow premium (indeed a
   negative contrast); pre-trend transparency as the methodological spine; the
   SFDR/SDR/SEC normative framing. Lead with the placebo identification and the
   pre-registration decision rule — the null is the contribution.
2. *(Optional, data-gated)* re-ingest the raw 13F INFOTABLE keyed by filer CIK to
   unlock H4 (passive/active, ESG-badged) — the only piece blocked on data, not code.

## 2026-06-06 (cont.) — PLACEBO ARM + MATCHED CONTROLS + CAR (task #9 / Phase 2b done)

**The identification scaffolding is now built: a generic-inclusion placebo, a
matched estimation sample, and a price-reaction secondary outcome. 27 tests green
(+14 this session).**

**1. S&P 500 placebo arm — the identification centrepiece.** The ESG-specific
effect is ESG-inclusion ATT − generic-inclusion ATT; S&P 500 additions are the
canonical generic event. The S&P events are ticker/name-keyed (Wikipedia) but the
panel is CUSIP-keyed (13F), and CUSIP is licensed — so `src/build/crosswalk.py`
builds a **CUSIP→issuer-name map from every cached 13F bundle** (equity-only,
modal name by filer-row support: **79,944 CUSIPs**) and matches S&P names onto it.
- The matcher does exact-normalised first, then a **prominence-tie-break subset
  fallback** (among issuers whose tokens superset the query, take the one with the
  most 13F support). This lifted coverage from a naive unique-subset rule's 79% to
  **92% (124/135 adds: 105 exact + 19 subset + 11 miss)**; the 11 misses are
  recent spin-offs/IPOs/renames (FDXF, EXE, SOLS, …). Spot-checked subset hits are
  correct (Carrier→CARRIER GLOBAL, NXP→NXP SEMICONDUCTORS N V, GE HealthCare→GE
  HEALTHCARE TECHNOLOGIES).
- `src/build/placebo.py` maps S&P adds→CUSIP and exposes the ever-S&P-500 pool;
  `panel.py` now runs a **symmetric `sp500_*` cohort arm**. Placebo: **123 treated,
  787 ever-members, 99 estimable. 58 firms are BOTH ESG- and S&P-treated**
  (`both_treated`) — a real contamination point — leaving **65 clean-generic**
  (S&P-add but never-ESG) firms for the contrast. Documented, not hidden.

**2. Matched controls (`src/build/matching.py`).** The naive 95k never-treated
pool is wildly inappropriate: treated firms sit **>2 SDs above pool mean** on size
(|SMD| ≈ 2.1–2.5), because index-eligible large caps vs. the micro-cap universe.
- Per-cohort matching at the **baseline quarter g−1** (so calendar/level
  confounding is differenced out by the match), on the pre-treatment ownership
  covariates the CUSIP panel carries directly: `log_value` (size proxy),
  `log_shares`, `n_filers` (breadth). Two methods (**PSM** = pooled propensity w/
  quarter FE + NN on the logit; **CEM** = quantile-bin exact strata), run
  **symmetrically for both arms**. Result: ESG **332/332** and S&P **101/101**
  matched, 0 unmatched; balance collapses to **|SMD| < 0.05 (CEM)** / **< 0.15
  (PSM)** — the matched sample is a credible counterfactual where the raw pool was
  not. Saved `data/processed/matched_{esg,sp500}_{psm,cem}.parquet`.
- *Limitation, logged:* sector (GICS, free only for current S&P members) and a
  price-based liquidity measure aren't in the CUSIP panel; they're accepted as
  optional covariates when joined in, not silently omitted.

**3. FF-adjusted CAR — the secondary (price) outcome (`src/build/car.py`).** A
five-factor market-model event study (estimation window ≈1yr ending −22d;
abnormal = actual−predicted excess; CAR = sum).
- **Runs on the S&P placebo arm, honestly not the ESG arm.** A daily event study
  needs a priceable ticker *and* a precise date; S&P adds have both (Wikipedia
  effective dates + tickers), the ESG inclusions have **neither at resolution**
  (no free CUSIP→ticker bridge; N-PORT gives only *quarterly* inclusion timing).
  So the generic-inclusion CAR is the deliverable; the ESG question stays on the
  fully-covered quarterly flow design.
- Recovers the **modern S&P 500 index effect**: CAR[−5,+5] = **+1.35% (t=1.55,
  n=99, 54% positive)** over the announce-to-effective window — attenuated to ~1%
  exactly as the post-2010s arbitraged-era literature predicts; tight windows ≈0.
  Coverage reported (99 ok; 20 insufficient pre-history = recent IPOs; 3 delisted:
  CTLT/FRC/CDAY). Saved `data/processed/car_sp500.parquet`.

### Next
1. **Phase 3 estimation.** Freeze `PREREGISTRATION.md`; install the conda econ
   stack (`conda install -c conda-forge pyfixest polars numba differences`);
   implement `src/estimate/did.py` — Callaway-Sant'Anna + Sun-Abraham event study
   around *first* inclusion (ITT, since non-absorbing), mandatory pre-trends test,
   the **ESG-vs-placebo contrast**, the post-2022 decay break, and passive/active
   13F heterogeneity. Run on both the full clean-control and the matched samples.

## 2026-06-06 (cont.) — FIRM×QUARTER PANEL ASSEMBLED (task #8 / Phase 2 done)

**`src/build/panel.py` implemented — the analysis dataset now exists.**
- `build_panel()` joins the three interim tables (13F outcome + N-PORT treatment
  + ESG membership) into `data/processed/panel.parquet`: **904,589 rows, 95,572
  CUSIPs, 29 quarters (2019Q1→2026Q1)**. `make panel` now runs the build (was a
  hard-gated stub); **13 tests green** (added 7 in `tests/test_panel.py` covering
  cohort timing, quarter alignment, the unit normalisation, junk-drop, the gap
  rule, sample roles and reversal).
- **Quarter alignment works as designed:** both the N-PORT fiscal quarter-ends
  (Feb/May/Aug/Nov) and the 13F calendar quarter-ends fold onto the **containing
  calendar quarter** — a 2020-02-29 inclusion and the 2020-03-31 13F snapshot
  both land in 2020Q1 and join cleanly. Cohort = first genuine inclusion quarter;
  `event_time` in quarters; `post`/`esg_inclusion` absorbing from cohort.
- **2023 VALUE unit change handled + empirically pinned.** Boundary confirmed at
  report period **2022-12-31** (MSFT total_value 14.76B at 2022-09-30 → 1,086B at
  2022-12-31; cross-firm median 1,407 → 407,346). `total_value` ×1000 for periods
  ≤ 2022-09-30 → `total_value_usd`; `n_filers` and `total_shares` are unit-immune
  and so are the **primary** outcomes (breadth + share depth).
- **Junk dropped:** non-9-char and issuer-base-`000000` CUSIPs (the `N/A`
  placeholder, `0000000NA`, etc.) — 457 rows / 408 ids out of the 13F panel.

**Two identification calls made explicitly (not papered over).**
- **Left-censored members are NOT controls.** The membership panel starts 2019Q4,
  so the ~289 firms already in the index at the window start have no datable
  inclusion. Those + corp-action-suspect adds are tagged **`esg_excluded`** and
  held OUT of the never-treated pool. Final roles: **334 treated / 95,035 clean
  controls / 203 esg_excluded.** 332/334 treated have both pre & post observed.
- **Treatment is non-absorbing — a real finding.** **177/334 treated firms later
  exit the index** (`ever_dropped` flag). Canonical Callaway-Sant'Anna assumes
  absorbing treatment, so the headline will be an **event study around *first*
  inclusion (ITT)**; long-horizon ATT is attenuated by exits. Documented for
  Phase 3, not hidden.
- **Caution, honestly logged:** raw treated-group breadth rises around inclusion
  (event-time −3→0→+3: 806→873→922) **but with a pre-trend in the pre-period
  itself** (−3→−1: 806→836). So the raw means are *not* the causal estimate — the
  clean-control + S&P-500-placebo DiD and a pre-trends test are what isolate any
  ESG-specific effect. The panel surfaces both the signal and the caveat.

### Next
1. `src/build/matching.py` — matched controls (size/sector/pre-ownership/liquidity)
   → the estimation sample, symmetrically for ESG and the placebo.
2. Persist S&P 500 placebo events (`sp500_events.py` has no `to_parquet` yet) and
   build the placebo arm; FF-adjusted CAR needs the full price pull.
3. Phase 3 estimation (`differences`/`pyfixest`) — needs the conda econ stack
   (`conda install -c conda-forge pyfixest polars numba differences`).

## 2026-06-06 — 13F OUTCOME PANEL BUILT (task #7 done); all data sources in

**13F institutional-ownership panel pulled end-to-end — the primary outcome.**
- `build_13f_panel()` now drives the full pipeline: `list_datasets()` discovers
  **both** SEC bundle naming conventions (old `2019q1_form13f.zip` back to 2013Q2;
  new receipt-window `01mar2024-31may2024_form13f.zip`), downloads in parallel,
  parses, and aggregates per CUSIP×quarter. Persisted
  `data/interim/holdings_13f.parquet`: **988,292 CUSIP×quarter rows, 29 quarters
  (2019Q1→2026Q1), 97,660 distinct CUSIPs**, n_filers rising ~2,750→6,128 over the
  window (more institutions filing over time — expected).
- **Coverage check passes:** the 481 genuine ESG inclusions span 335 distinct
  CUSIPs; **334/335 (99.7%) appear in the 13F panel** — the sole miss is an `N/A`
  placeholder CUSIP in the treatment (Phase-2 drop). Treatment ↔ outcome join is
  clean (all panel CUSIPs are 9-char).
- **Identification nuance handled:** 13F bundles are keyed by *filing-receipt
  window*, not report quarter — so each is filtered to its **modal
  `PERIODOFREPORT`** and deduped to the **latest filing per CIK** (an amendment
  supersedes its original, so `n_filers` counts distinct institutions, not
  filings). Modal filtering drops ~3% late stragglers landing in an adjacent
  window (minor n_filers undercount, documented). e.g. `2019q1_form13f.zip`
  correctly reports quarter-end **2018-12-31**, not "2019Q1".
- 6 tests still green (pure cores unchanged).

**Two infra failures found and fixed (the pull had silently died overnight).**
- **It wasn't slow — it was dead.** The first background run stopped after ~26h
  of zero progress with no traceback: the Mac slept while unattended and
  suspended/killed the job. Fix: run under **`caffeinate -ims`** so the machine
  can't sleep mid-pull. Also the per-bundle download was crawling (~150 KB/s,
  sequential, single-stream, power-nap-throttled).
- **New streaming downloader** `edgar_session.edgar_download()`: streams to a
  `.part` file with a per-read timeout (a stalled socket now fails fast + retries
  instead of hanging for days), atomic rename on success (a cached file is always
  complete), block-detection on the first chunk only (no charset-sniffing a 90 MB
  zip via `resp.text`). `build_13f_panel()` downloads **5 bundles in parallel** →
  **~24 MB/s** (~160× faster) and **checkpoints one parquet per bundle** under
  `data/interim/_13f_parts/`, so any interruption resumes from disk.
- **SEC zip-layout quirk:** most bundles store TSVs at the zip root, but
  `01jun2025-31aug2025` nests them under a subfolder. `parse_dataset()` now
  matches members by **basename** (handles both). This was the `KeyError:
  'INFOTABLE.TSV'` that aborted the first complete run.

### Next
1. Task #8 / Phase 2 — firm×quarter panel: align N-PORT fiscal-quarter as-of dates
   (Feb/May/Aug/Nov) to 13F calendar quarters (Mar/Jun/Sep/Dec); join treatment +
   outcome + prices + FF + S&P 500 placebo; normalise the 13F $thousands→whole-$
   unit change pre-2023; exclude `corp_action_suspect` events and the `N/A`-CUSIP
   junk; reconcile changed-name corp actions.
2. Commit `make data-sec` outputs' lineage; both SEC sources now land via one
   `make data-sec` (run under `caffeinate`).

## 2026-06-05 (cont. 2) — SEC UNBLOCKED end-to-end; N-PORT treatment BUILT

**SEC access fully resolved — two stacked filters, both fixed.**
- Cause 1: datacenter/VPN egress IP (Datacamp/Dublin) — fixed by turning the VPN
  off → residential ISP. Cause 2: the UA contact email was non-deliverable
  (`…@users.noreply.github.com`), which SEC *also* 403s — fixed with a real
  contact in the gitignored `.env`. With both fixed, every SEC host returns 200.
  `edgar_session._DEFAULT_UA` now fails closed (no fake contact) and
  `_egress_diagnosis()` flags a datacenter IP so a future clone behind a VPN
  explains itself.

**N-PORT treatment BUILT — `build_inclusion_events()` (task #6 done).**
- Discovery via browse-EDGAR atom by *series* id (SUSL S000065418, SUSA
  S000004436 in iShares Trust CIK 1100663); holdings from each filing's
  `primary_doc.xml`. N-PORT-P is **quarterly**, not monthly (corrected in code,
  README, DATA_LINEAGE). As-of = `repPdDate` (quarter-end, e.g. 2026-02-28) —
  deliberately NOT `repPdEnd` (the fund's Aug-31 fiscal-year end, a constant that
  would collapse quarters).
- Pulled SUSL+SUSA 2020→2026: **946 raw add/drop events** (494 adds). Persisted
  `data/interim/esg_index_holdings.parquet` (membership panel) +
  `esg_inclusion_events.parquet` (treatment). Reconstitution spikes show up as
  expected (SUSL 2023-08: 62 adds, 2022-08: 55).
- **Data-quality finding (matters for identification):** a pure CUSIP diff turns
  corporate actions into fake inclusions — ~20% of adds have a same-quarter
  name-similar drop. Added a conservative `corp_action_suspect` flag (exact
  normalized-name same-quarter add+drop = split/redomicile churn): **27 flagged
  → 481 genuine inclusions.** Changed-name renames/mergers (AXA Equitable→
  Equitable; BB&T+SunTrust→Truist; Arconic→Howmet) evade exact-name matching and
  are a documented Phase-2 reconciliation step (not silently dropped).
- 6 tests still green (pure cores unchanged).

### Next
1. Task #7 — 13F outcome: run the `edgar_13f` half of `make data-sec` (quarterly
   bundles → `aggregate_ownership`; handle the 2023-01 $thousands→$ unit change).
2. Task #8 / Phase 2 — firm×quarter panel: align N-PORT fiscal-quarter as-of
   dates (Feb/May/Aug/Nov) to 13F calendar quarters (Mar/Jun/Sep/Dec); join
   treatment + outcome + prices + FF + S&P 500 placebo; reconcile changed-name
   corp actions; exclude `corp_action_suspect` events.

## 2026-06-05 (cont.) — Phase 0 finalised + pushed; SEC blocker ROOT-CAUSED

**Phase 0 artifacts finished and shipped.**
- `Makefile` with targets `data` / `data-sec` / `panel` / `estimate` / `placebo`
  / `figures` / `test` / `clean` (Phase 2-5 targets fail loudly until data-sec
  lands — by design). `requirements.lock` pins the 128-package Phase-1 env.
  `.gitignore` now also excludes `data/interim/*` and `.virtual_documents/`.
- Committed `91b6582` and **pushed to origin/main**. 6 tests green.

**SEC blocker ROOT-CAUSED — it's a VPN, not a code or SEC-policy problem.**
- The egress IP `149.34.242.15` geolocates to **Datacamp Limited (AS212238),
  Dublin IE, flagged `proxy:true hosting:true`** — i.e. a datacenter VPN exit
  node. SEC's Akamai bot-manager blocks datacenter/VPN/proxy IPs wholesale,
  which is why *every* client got 403 regardless of User-Agent or TLS.
- Ruled out the alternatives this session: `curl_cffi` Chrome **and** Safari TLS
  impersonation still 403 (not a TLS-fingerprint issue); the declared UA is
  transmitted correctly via httpbin (not a UA-clobbering issue). The two block
  pages seen — "Request Rate Threshold Exceeded" (www) and "Undeclared Automated
  Tool" (data) — are Akamai's canned 403s for a flagged IP.
- **Fix (Jimmy's action):** turn off the VPN so traffic egresses from a
  residential ISP, confirm `https://www.sec.gov/` loads in the browser, then
  `make data-sec`. `edgar_session._egress_diagnosis()` now detects a
  datacenter egress IP and appends a "turn off your VPN" line to `EdgarBlocked`,
  so the failure is self-explanatory on any future clone.

### Next
1. Jimmy: disable VPN → `make data-sec` from residential network. Gates Phase 2-5.
2. Phase 2 — build `data/processed/panel.parquet` once 13F + N-PORT land.
3. Phase 3 — freeze `PREREGISTRATION.md`, install the conda econ stack, estimate.

## 2026-06-05 — Phase 0 complete; Phase 1 partial (reachable done, SEC blocked)

**Phase 0 (repo restructure) — DONE.**
- Reconciled the April scaffold (flat `src/`, an older ESG *rating-change → flows*
  design with an IV / reverse-causality framing) to the refined build plan:
  treatment is now **index inclusion itself**, headline is the **S&P 500 placebo**
  (ESG-specific effect = ESG-inclusion − generic-inclusion), plus **post-2022
  legitimacy decay**, using heterogeneity-robust staggered DiD.
- New structure: `src/{ingest,build,estimate,viz,utils}/`, `tests/`, `paper/`.
  Removed stale stubs (`data_loader.py`, `panel_builder.py`, `causal_models.py`,
  `viz.py`). Estimator scaffolds now encode the new design (event study,
  Callaway-Sant'Anna, Sun-Abraham, placebo, structural break, heterogeneity).
- `requirements.txt` re-aligned to the plan stack (added pyfixest, differences,
  polars; dropped dowhy/causalml/econml). `requirements.lock` snapshots the
  working Phase-1 env.

**Phase 1 (data) — reachable sources DONE, SEC sources WRITTEN but BLOCKED.**
- ✅ Fama-French daily factors — 15,813 rows, 1963→2026 (`src/ingest/ff_factors.py`).
- ✅ S&P 500 placebo events — 754 add/drop events, 1976→2026 (`src/ingest/sp500_events.py`).
- ✅ Prices — yfinance verified on a sample (`src/ingest/prices.py`).
- ✅ Tests — 6 pass: 3 reachable-data smoke + 3 SEC-transform unit tests on
  synthetic data (`aggregate_ownership`, `parse_nport_xml`, `compute_inclusion_events`).
- ⛔ **13F (primary outcome) + N-PORT (treatment) — blocked.** SEC returns 403 to
  every client from this environment's IP (`149.34.242.15`); it is IP-level
  Akamai blocking, not a code bug. Code is written, compliant, and its pure cores
  are unit-tested. See `data/DATA_LINEAGE.md` access note.
- 🔒 Index-event source **LOCKED** to SEC N-PORT-P monthly-holdings diff (Wayback
  had no iShares captures; the live CSV has no history).

**Env caveat:** the venv is an Intel/Anaconda Python 3.12 with bleeding-edge
numpy 2.4 / pandas 3.0. `pyfixest`→numba/llvmlite and source-only builds fail
without cmake; **defer with `conda install -c conda-forge pyfixest polars numba`**
on the analysis machine (Phase 3). Ingestion needs none of these.

### Open items / next
1. **Unblock SEC** (owner: Jimmy). Confirm sec.gov loads in your browser; run
   `make data-sec` from an unblocked network, or decide an alternative. This gates
   Phases 2-5.
2. Phase 2 — build `data/processed/panel.parquet` once 13F + N-PORT land.
3. Phase 3 — freeze `PREREGISTRATION.md`, then estimate (needs the conda econ stack).
