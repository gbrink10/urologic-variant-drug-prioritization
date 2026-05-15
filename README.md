# Public Genomic and Transcriptomic Drug Prioritization for Aggressive Urologic Cancer Variants

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20217919.svg)](https://doi.org/10.5281/zenodo.20217919)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)

Code and processed result tables supporting:

**Brinkley GJ, Greenberg J, Caso J.** *Biomarker-Matched Therapeutic Prioritization for Rare Aggressive Urologic Cancer Variants Using Public Genomic and Transcriptomic Data.* (Under review, 2026.)

Department of Urology, Tulane University School of Medicine, New Orleans, Louisiana, USA.

**Permanent archive:** Zenodo DOI [10.5281/zenodo.20217919](https://doi.org/10.5281/zenodo.20217919)

---

## What this is

A reproducible computational framework that integrates **TCGA PanCancer Atlas alteration frequencies**, **GEO transcriptomic / kinome expression data**, and **KEGG pathway enrichment** to prioritize biomarker-matched therapeutic hypotheses for three rare aggressive urologic cancer variants:

- **NEPC** — neuroendocrine prostate cancer
- **MPBC-applicable** — micropapillary bladder cancer, framed via MIBC kinome biology
- **sRCC-applicable** — sarcomatoid renal cell carcinoma, framed via ccRCC/HLRCC HIF/VEGF biology

The framework outputs **16 drug–cancer associations spanning 15 therapeutic candidates**, each assigned a **9-point molecular prioritization score** (TCGA + GEO + KEGG + external literature). Phase III source-disease trial concordance is reported as a separate flag, not as part of the score.

## Repository layout

```
.
├── code/                              # Analysis scripts
│   ├── geo_full_de_kegg.py            # Main DE + KEGG pipeline
│   ├── compute_drug_scores.py         # 10-point scoring (legacy; v12)
│   ├── update_scores_9pt.py           # 9-point scoring (v18; current)
│   ├── cbioportal_verify.py           # TCGA frequency verification
│   ├── cbioportal_verify2.py          # Combined alteration check (mut + CNA + SV)
│   ├── build_figure1.py               # TCGA molecular landscape (Figure 1)
│   ├── build_score_figures.py         # Per-cancer score panels (legacy)
│   ├── rebuild_score_figures_v18.py   # 9-point score panels (current)
│   ├── build_figure5_heatmap.py       # Evidence-concordance heatmap (Figure 5)
│   └── build_supp_table_s2.py         # Supplementary Table S2 builder
│
├── data/                              # Processed result tables
│   ├── FULL_DE_RESULTS.csv            # Per-gene Welch/paired t-stats, log2FC, p, BH-q
│   ├── KEGG_ENRICHMENT.csv            # Pathway-level OR + nominal p
│   ├── DRUG_EVIDENCE_SCORES_v18.csv   # 9-point molecular scores + Ph III concordance flag
│   ├── DRUG_EVIDENCE_SCORES_v12.csv   # Legacy 10-point scores (historical)
│   └── Supplementary_Table_S2_expanded_drug_list.csv
│
└── figures/                           # Manuscript figures (PNG, 300 DPI)
    ├── figure1_TCGAfixed.png          # TCGA molecular landscape
    ├── figure2E_NEPC_drug_scores.png  # NEPC drug prioritization panel
    ├── figure3E_MIBC_drug_scores.png  # MIBC drug prioritization panel
    ├── figure4E_sRCC_drug_scores.png  # ccRCC/sRCC drug prioritization panel
    └── figure5_evidence_concordance_heatmap.png
```

## Data sources

All input data are publicly available; this repository contains only **processed results**, not raw data.

### TCGA PanCancer Atlas (via cBioPortal)

- BLCA: `blca_tcga_pan_can_atlas_2018` (n = 411 patients)
- KIRC: `kirc_tcga_pan_can_atlas_2018` (n = 512 patients)
- PRAD: `prad_tcga_pan_can_atlas_2018` (n = 494 patients)

Alteration frequencies queried via cBioPortal REST API on 2026-05-13.

### GEO expression datasets

| Accession   | Description                                                   | n  |
|-------------|---------------------------------------------------------------|----|
| GSE199274   | MDVr NEPC-like cells; CXCR7 knockdown                         | 12 |
| GSE216053   | PM154 NEPC patient-derived model; ± decitabine (day 14)       | 6  |
| GSE216052   | PM154 with DNMT1 / DNMT3A knockout                            | 9  |
| GSE130598   | MIBC tumor vs adjacent normal (NanoString ~522-gene kinome)   | 48 |
| GSE143630   | ccRCC; stage pT1 vs pT2 sample-name partition                 | 44 |
| GSE157256   | HLRCC + aggressive/metastatic RCC                             | 26 |

## How to reproduce

### Requirements

- Python 3.10+
- `pip install -r requirements.txt`

### Quick start

```bash
# Recompute the 9-point molecular prioritization scores
python code/update_scores_9pt.py

# Regenerate the per-cancer drug-prioritization figure panels
python code/rebuild_score_figures_v18.py

# Regenerate the evidence-concordance heatmap (Figure 5)
python code/build_figure5_heatmap.py
```

The processed data tables (`data/FULL_DE_RESULTS.csv`, `data/KEGG_ENRICHMENT.csv`) were generated by `code/geo_full_de_kegg.py` from the GEO accessions listed above. The raw GEO expression matrices required to re-run the upstream pipeline are downloadable from NCBI GEO under the accessions above.

## Methodology summary

- **Differential expression:** Python 3.10 + `scipy.stats`. Paired two-sided t-test was primary for GSE130598 (matched-pair design); Welch t-tests were primary for all other comparisons. Benjamini–Hochberg FDR was applied within each comparison. Hypothesis-generating threshold: |log2FC| ≥ 0.5 with p < 0.05.
- **KEGG pathway enrichment:** Upper-tail hypergeometric test (`scipy.stats.hypergeom.sf`) against eight pre-specified pathways (Cell Cycle hsa04110, PI3K-AKT hsa04151, HIF-1 hsa04066, VEGF hsa04370, p53 hsa04115, Homologous Recombination hsa03440, Apoptosis hsa04210, Epigenetic Regulation custom set). Background gene sets matched each dataset's profiling scope (whole-transcriptome for RNA-seq; ~522-gene NanoString panel for GSE130598). KEGG gene sets retrieved from the KEGG REST API (April 2026 release).
- **Drug prioritization score (0–9):** TCGA genomic evidence (0–3) + GEO transcriptomic evidence (0–3) + KEGG pathway enrichment (0–2) + external literature concordance (0–1). Composite scores: Strong ≥ 7, Moderate 4–6, Exploratory ≤ 3.
- **Phase III source-disease concordance:** Reported separately from the molecular score (not part of the 0–9 composite). Concordant trials cited in `DRUG_EVIDENCE_SCORES_v18.csv` `phase3_trial` column.

## Citation

If you use this code or any of the processed tables, please cite:

```
Brinkley GJ, Greenberg J, Caso J. Biomarker-Matched Therapeutic Prioritization for
Rare Aggressive Urologic Cancer Variants Using Public Genomic and Transcriptomic Data.
2026. https://github.com/gbrink10/urologic-variant-drug-prioritization
DOI: 10.5281/zenodo.20217919
```

## License

- **Code** (`code/`): MIT License — see [LICENSE](LICENSE).
- **Processed data tables** (`data/`): CC-BY 4.0.
- **Figures** (`figures/`): CC-BY 4.0.

## AI usage disclosure

Claude (Anthropic) was used for coding assistance, language editing, and manuscript-structure suggestions during preparation. All analyses were executed by author-run Python scripts using publicly available datasets. All quantitative values, interpretations, and final text were reviewed and approved by the authors, who take full responsibility for the content.

## Contact

Corresponding author: Garrett J. Brinkley, MD — garrettjbrinkley@gmail.com
