# ARCHIVE — `legacy/v25/`

> ## This folder is NOT the deposit referenced by the current manuscript.

The files in this folder belong to an **earlier three-context analysis** (v25: neuroendocrine prostate cancer, muscle-invasive bladder cancer, clear cell renal cell carcinoma) that produced 16 drug–cancer associations across the source-disease contexts.

**It has been superseded** by the v26 expansion at the root of this repository:

- Seven clinical contexts (the three source-disease contexts plus four rare-disease / variant-histology contexts: renal medullary carcinoma; penile squamous cell carcinoma; sarcomatoid urothelial carcinoma; lineage-transcription-factor-stratified small-cell bladder cancer)
- Ten Gene Expression Omnibus datasets
- Eighteen pre-specified KEGG pathways
- **Thirty drug–cancer associations** (Master Table 1)

## What this folder is NOT

- It is **not** the data backing any claim made in the v26 manuscript.
- Its CSV files (`FULL_DE_RESULTS.csv`, `KEGG_ENRICHMENT.csv`, `DRUG_EVIDENCE_SCORES_v18.csv`, `GEO_DATASET_AUDIT.csv`, etc.) are **earlier-iteration files** retained only so v25 commits/tags remain reproducible from disk.
- For reproducing the v26 manuscript, use the files at the root of the repository:
    - `data/DE_results/FULL_DE_RESULTS_ALL10.csv`
    - `data/DE_results/GEO_DATASET_AUDIT_10_DATASETS.csv`
    - `results/MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv`
    - `results/PUBMED_NOVELTY_AUDIT.csv`
    - `results/KEGG_PATHWAYS_18.json`, `results/KEGG_ENRICHMENT_ALL10.{json,csv}`

## Why these files were retained

The v26 expansion was developed iteratively from v25. Preserving v25 intermediate artifacts under `legacy/v25/` keeps the historical record auditable from disk. Reviewers and editors evaluating the current manuscript should ignore this folder.
