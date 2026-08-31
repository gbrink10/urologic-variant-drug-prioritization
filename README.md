# Auditable public-data prioritization of drug hypotheses in urologic cancers

Code and results for the manuscript *An Auditable Public-Data Framework for
Prioritizing Biomarker-Matched Drug Hypotheses Across Benchmark and Rare
Urologic Cancers* (v29).

The framework applies one pipeline uniformly to seven contexts — three common
diseases that serve as benchmarks and four rare or variant diseases where it is
asked to discover — and reports what it cannot support as explicitly as what it
can.

Everything in `code/pipeline/` resolves its paths through `paths.py` and runs
from a clone of this repository. No file needs editing to run it elsewhere.

## Running it

```bash
python code/pipeline/30_fetch_raw_matrices.py      # ~820 MB from GEO
python code/pipeline/31_fetch_sample_metadata.py   # series matrices
python code/pipeline/37_hgnc_symbol_map.py         # HGNC symbol table
python code/pipeline/32_prepare_matrices.py        # standardised matrices + metadata

Rscript code/pipeline/33_refit_limma.R .           # limma / edgeR refit

python code/pipeline/34_compare_refit_to_published.py
python code/pipeline/35_refit_enrichment.py
python code/pipeline/36_rmc_reanalysis.py
python code/pipeline/38_extract_row_definitions.py
python code/pipeline/39_rescore_from_refit.py
python code/pipeline/41_candidate_selection.py
python code/pipeline/43_audit_downstream_coverage.py
python code/pipeline/44_lincs_connectivity_v29.py  # needs network (Enrichr)

python code/pipeline/40_figure2_rmc_v29.py
python code/pipeline/42_figure5_selection_v29.py
python code/pipeline/46_figures_3_4_v29.py
python code/pipeline/47_manuscript_facts.py
python code/pipeline/48_build_manuscript_v29.py
python code/pipeline/50_build_cover_letter_v29.py
python code/pipeline/49_audit_manuscript_v29.py    # 53 checks, all must pass
```

Requirements: Python 3.10 with numpy, scipy, pandas, matplotlib, python-docx,
Pillow; R 4.6 with Bioconductor `limma` and `edgeR`. Two directories can be
redirected with the environment variables `UVDP_FIGURES` and `UVDP_OUTPUT`.

Large third-party downloads (the GEO deposits, the HGNC table, the DepMap and
PRISM matrices) are not committed. The fetch scripts above retrieve them;
`data/cache/` holds the DepMap and PRISM files, whose download links are in the
header of each script that uses them.

## What is where

| Path | Contents |
| --- | --- |
| `code/pipeline/` | the analysis, numbered in execution order |
| `code/pipeline/paths.py` | every path the pipeline uses |
| `code/pipeline/lib_limma.py` | independent Python implementation of the moderated-t machinery, used as a cross-check on the R results |
| `code/manuscript_build/` | scripts that produced the v25–v28 manuscripts; kept for reconstructibility, not part of the current pipeline |
| `data/master_row_definitions.csv` | the curated half of the association table: drug, target, genomic frequency, stage, prior-proposal status |
| `results/refit/` | everything the v29 manuscript cites |
| `figures/` | the five manuscript figures |

## How the association table is built

The table has a curated half and a computed half, and they are kept apart on
purpose. A human supplies the drug, the target, the genomic frequency and its
published source, the clinical stage and the prior-proposal status; these live
in `data/master_row_definitions.csv`. The transcriptomic and pathway components,
the total and the tier are computed by `39_rescore_from_refit.py` from the
fitted tables. Earlier versions typed both halves by hand, which is how the
manuscript table and the deposited table came to disagree in 42 fields.

## Reproducibility notes, including what does not reproduce

- `33_refit_limma.R` fits each platform with its standard treatment: counts by
  `filterByExpr` + TMM + voom, log-scale series by limma-trend with robust
  eBayes, the penile series blocked on donor by duplicate correlation, the
  kinome panel paired on patient, the small-cell series batch-adjusted.
- `51_crosscheck_python_vs_r.py` compares the R fit against the independent
  Python implementation. On the like-for-like design the log-fold changes agree
  to 1.6e-14 and 99% of significant genes are shared.
- **GSE128192 is completely confounded.** All 28 sarcomatoid samples were run on
  4 array chips and all 84 conventional samples on 15 different chips, with none
  shared, so `~ chip + group` is not estimable and batch cannot be separated
  from biology for those rows.
- **GSE143630 contains no normal tissue**, so the clear cell rows are scored on
  absolute expression rather than a disease contrast.
- **GSE180999 deposits no sample-level matrix**, only an author
  differential-expression spreadsheet, so a cell-line × treatment × time model
  cannot be fitted from deposited data. `36_rmc_reanalysis.py` instead treats the
  two patient-derived lines as two biological replicates and scores only genes
  changing consistently in both.
- Rows whose target is absent from its platform keep a curated value and are
  flagged in the provenance table rather than silently scored.

## Superseded code

Scripts marked `SUPERSEDED (v29)` in their header produced the v26–v28 analysis
and are retained so those versions remain reconstructible. They are not part of
the current pipeline. In particular, the earlier enrichment used a fixed
20,000-gene universe and did not normalise gene symbols, which silently dropped
renamed genes — including IL8/CXCL8 — from the pathways they define.

## Citation

Brinkley GJ, Greenberg J, Caso J. *An Auditable Public-Data Framework for
Prioritizing Biomarker-Matched Drug Hypotheses Across Benchmark and Rare
Urologic Cancers.* Manuscript in preparation.
