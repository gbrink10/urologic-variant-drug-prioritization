# v31.0 — submitted analysis

The analysis, figures, manuscript, cover letter and Supplementary Methods as
submitted to JCO Clinical Cancer Informatics.

## What this release contains

One pipeline applied uniformly to seven contexts — three better-studied
benchmarks and four rare or variant urologic cancers. An earlier implementation
generated a 30-association candidate set; membership was frozen before
design-aware refitting, and the models in this release re-estimate the
transcriptomic and pathway evidence for that fixed set, recalculate scores and
tiers, and apply the eligibility and orthogonal-audit rules to it.

Twenty-five associations remain scoreable. Five sarcomatoid rows carry no score
because histology is completely aliased with array chip in GSE128192 and the
contrast is therefore not estimable. Six associations without a prior
urologic-oncology proposal reduce to three survivors across two diseases.

## What changed since the earlier archive

- Every deposited dataset refitted with a design-aware, platform-appropriate
  model (limma / edgeR) rather than reused summary statistics.
- Enrichment now uses each dataset's own measured-gene universe and current HGNC
  symbols; the earlier fixed 20,000-gene universe and unnormalised symbols had
  silently dropped renamed genes, including IL8/CXCL8, from their own pathways.
- PRISM compares urothelial against non-urothelial lines by two-sided Welch test
  with Benjamini-Hochberg correction, not urothelial against a panel containing
  them.
- The manuscript is generated from the deposited result tables and reconciled
  against them by a 71-check audit script.

## Limits recorded in the deposit

- `results/refit/CANDIDATE_UNIVERSE.csv` gives the candidate denominator per
  analysis unit but marks the gene-to-druggable-target mapping counts as not
  reconstructible: that step was performed by hand and its query log was not
  retained.
- `results/refit/PRIOR_PROPOSAL_AUDIT.csv` records the per-row classification,
  its citations, the search template and the counting rules. One reviewer, no
  duplicate classification, per-row query strings not logged.

Large third-party primary data are re-downloaded by the fetch scripts rather
than mirrored here.
