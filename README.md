# Urologic Variant Drug Prioritization — Public-Data Pipeline

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20217919.svg)](https://doi.org/10.5281/zenodo.20217919)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)

A reproducible public-data pipeline that identifies convergent and novel drug-repurposing priorities across rare aggressive urologic cancers.

## What this repository contains

This repository archives the analytical scripts, intermediate result tables, KEGG pathway artifacts, master drug-cancer association table, and generated figures for the manuscript:

**"A Reproducible Public-Data Pipeline Identifies Convergent and Novel Drug-Repurposing Priorities Across Rare Aggressive Urologic Cancers"** *(under review)*

Authors: Garrett J. Brinkley, MD; Jacob Greenberg, MD; Jorge Caso, MD
Department of Urology, Tulane University School of Medicine

## v25 → v26 expansion

The original repository was organized for a three-context source-disease analysis (neuroendocrine prostate cancer; muscle-invasive bladder cancer; clear cell renal cell carcinoma). In v26 the pipeline has been expanded to seven aggressive urologic cancer contexts and integrates ten Gene Expression Omnibus transcriptomic datasets, eighteen pre-specified KEGG pathways, a 9-point Molecular Prioritization Score, and an independent PubMed prior-proposal audit per drug-cancer association.

### Seven clinical contexts

1. Neuroendocrine prostate cancer (NEPC)
2. Muscle-invasive bladder cancer (MIBC)
3. Clear cell renal cell carcinoma (ccRCC)
4. Renal medullary carcinoma (RMC) — SMARCB1-deficient
5. Penile squamous cell carcinoma (PSCC)
6. Sarcomatoid urothelial carcinoma
7. Small-cell bladder cancer (SCBC) — lineage-transcription-factor-stratified (ASCL1+, NEUROD1+, POU2F3+, YAP1+)

### Master output

**30 drug-cancer associations** across the seven contexts:
- **18** converge on previously-proposed urologic-oncology priorities (convergent literature support)
- **6** are framework-novel within the urologic-oncology literature:
  - Chemokine receptor 1/2 antagonists (reparixin, navarixin, AZD5069) in RMC
  - Anti-CEACAM1 (CM24) in RMC
  - NSD2 inhibitors (KTX-1001, seclidemstat) in sarcomatoid urothelial carcinoma
  - ATR pathway inhibitors (ceralasertib, berzosertib, elimusertib) in sarcomatoid urothelial carcinoma
  - Lutetium-177 DOTATATE in NEUROD1+ SCBC
  - Tusamitamab ravtansine in ASCL1+ SCBC
- **5** are partially novel variant-specific extensions
- **1** is a clinically actionable negative biomarker (TROP2-low in sarcomatoid urothelial carcinoma predicts sacituzumab govitecan non-response)

## Repository structure (v26)

```
.
├── code/
│   ├── v26_pipeline/                    # Analysis pipeline (12 numbered scripts)
│   │   ├── 09b_kegg_fetch_fixed.py      # Fetch 18 KEGG pathway gene sets
│   │   ├── 01_rmc_de_analysis.py        # RMC differential expression
│   │   ├── 02_rmc_drug_targets.py       # RMC drug-target identification
│   │   ├── 03_penile_de_analysis.py     # Penile SCC DE (tumor vs normal)
│   │   ├── 04_sarcomatoid_uc_de.py      # Sarcomatoid UC DE (SARC vs conventional UC)
│   │   ├── 05_scbc_subtype_analysis.py  # SCBC subtype DE (lineage-TF stratified)
│   │   ├── 06_trcc_de.py                # Translocation RCC (exploratory)
│   │   ├── 07_consolidate_findings.py   # Cross-disease drug-target mapping
│   │   ├── 08_master_table1.py          # Initial master table build
│   │   ├── 10_uniform_scoring.py        # KEGG enrichment across all diseases
│   │   ├── 11_master_table_uniform.py   # Final 30-row Master Table with uniform 9-point scoring
│   │   └── 12_generate_figures.py       # Generate Figures 1-4
│   └── v26_manuscript_build/            # Manuscript generation scripts (docx assembly)
├── data/
│   ├── v26_DE_results/                  # Per-disease differential-expression result tables
│   │   ├── RMC_up_in_null_state.csv     # 13 cross-cell-line consistent UP genes in SMARCB1-null
│   │   ├── SarcomatoidUC_up.csv         # SARC vs conventional UC UP genes (q<0.05, log2FC>1)
│   │   ├── SarcomatoidUC_DE_full.csv.gz # Full Sarc-UC DE results (gzipped, 29,377 probes)
│   │   ├── SCBC_subtype_calls.csv       # Per-sample lineage TF subtype assignments
│   │   ├── SCBC_up_in_ASCL1.csv         # ASCL1+ subtype UP genes
│   │   ├── SCBC_up_in_NEUROD1.csv       # NEUROD1+ subtype UP genes
│   │   ├── SCBC_up_in_POU2F3.csv        # POU2F3+ subtype UP genes
│   │   ├── PenileSCC_tumor_up.csv       # Penile SCC tumor-UP genes (filtered)
│   │   └── PenileSCC_DE_full.csv.gz     # Full Penile SCC DE results (gzipped)
│   └── (v25 source-disease data preserved in original locations)
├── results/
│   ├── v26/
│   │   ├── MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv   # Central artifact
│   │   ├── KEGG_PATHWAYS_18.json                       # 18 pre-specified pathway gene sets
│   │   └── KEGG_ENRICHMENT_ALL10.json                  # Hypergeometric enrichment per disease
│   └── (v25 result tables preserved)
├── figures/
│   ├── v26/
│   │   ├── Figure1_pipeline.png          # Unified pipeline schematic
│   │   ├── Figure2_RMC.png               # Renal medullary carcinoma novel findings
│   │   ├── Figure3_SarcUC.png            # Sarcomatoid urothelial carcinoma novel findings
│   │   └── Figure4_SCBC.png              # Small-cell bladder cancer subtype-stratified findings
│   └── (v25 figures preserved)
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore
```

## Data sources

- **The Cancer Genome Atlas Pan-Cancer Atlas 2018** via cBioPortal API
- **Gene Expression Omnibus** (10 accessions): GSE199274, GSE216053, GSE216052, GSE130598, GSE143630, GSE157256, GSE180999, GSE196978, GSE128192, GSE269750
- **Kyoto Encyclopedia of Genes and Genomes** REST API (18 pathway gene sets)
- **Therapeutic Target Database** (accessed May 2026) and **OpenTargets** (release 2026.03)
- **FDA Drugs@FDA** database

## Running the pipeline

```bash
pip install -r requirements.txt
python code/v26_pipeline/09b_kegg_fetch_fixed.py      # Fetch 18 KEGG pathway gene sets
python code/v26_pipeline/01_rmc_de_analysis.py
python code/v26_pipeline/03_penile_de_analysis.py
python code/v26_pipeline/04_sarcomatoid_uc_de.py
python code/v26_pipeline/05_scbc_subtype_analysis.py
python code/v26_pipeline/10_uniform_scoring.py        # KEGG enrichment across all diseases
python code/v26_pipeline/11_master_table_uniform.py   # Build Master Table 1 with uniform 9-point scoring
python code/v26_pipeline/12_generate_figures.py       # Generate Figures 1-4
```

Note: scripts use absolute paths reflecting the development environment; adjust paths for your local setup.

## License

MIT. See `LICENSE`.

## How to cite

> Brinkley GJ, Greenberg J, Caso J. A Reproducible Public-Data Pipeline Identifies Convergent and Novel Drug-Repurposing Priorities Across Rare Aggressive Urologic Cancers. Zenodo. 2026. doi:10.5281/zenodo.20217919

(Manuscript citation pending publication acceptance.)

## AI usage disclosure

Claude (Anthropic) and ChatGPT (OpenAI) large-language-model tools were used for coding assistance, literature-audit organization, language editing, and manuscript-structure suggestions. All analyses were executed by author-run Python scripts using publicly available datasets. All PubMed novelty classifications, score component assignments, drug-target interpretations, and final manuscript text were reviewed and approved by the human authors.

## Contact

For questions about reproducibility or methodology, open an issue on GitHub or contact the corresponding author.
