# Urologic Variant Drug Prioritization — Public-Data Pipeline (v26)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20217919.svg)](https://doi.org/10.5281/zenodo.20217919)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)

A reproducible public-data pipeline that identifies convergent and novel drug-repurposing priorities across seven aggressive urologic cancer contexts.

---

> ### What is deposited at the root of this repository
>
> **Seven clinical contexts. Ten GEO datasets. Thirty drug–cancer associations (Master Table 1).** The processed analysis tables that accompany the v26 manuscript are located at the **root of this repository** and named:
>
> - `data/DE_results/FULL_DE_RESULTS_ALL10.csv` — consolidated DE across all ten GEO datasets
> - `data/DE_results/GEO_DATASET_AUDIT_10_DATASETS.csv` — ten-dataset accession audit with PMIDs
> - `results/MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv` — thirty drug–cancer associations with per-row scoring
> - `results/PUBMED_NOVELTY_AUDIT.csv` — per-row novelty classification
> - `results/KEGG_PATHWAYS_18.json` and `results/KEGG_ENRICHMENT_ALL10.{json,csv}` — eighteen pre-specified pathways + hypergeometric enrichment per disease
>
> Source manuscript: the v26 submission (under review, May 2026). The `legacy/v25/` subfolder preserves an earlier three-context analysis **for provenance only** and is **not** the active deposit; see [`legacy/v25/README.md`](legacy/v25/README.md).

---

## Companion manuscript

**"A Reproducible Public-Data Pipeline Identifies Convergent and Novel Drug-Repurposing Priorities Across Rare Aggressive Urologic Cancers"** *(under review, May 2026)*

Authors: Garrett J. Brinkley, MD; Jacob Greenberg, MD; Jorge Caso, MD
Department of Urology, Tulane University School of Medicine

## What this pipeline does

The pipeline integrates:
- **The Cancer Genome Atlas Pan-Cancer Atlas 2018** alteration frequencies via cBioPortal
- **Ten Gene Expression Omnibus** transcriptomic datasets across seven clinical contexts
- **Eighteen pre-specified KEGG pathways** mapped to clinically-developed drug classes
- **Therapeutic Target Database** and **OpenTargets** drug-target curation
- A **9-point Molecular Prioritization Score** (TCGA-equivalent genomic + GEO transcriptomic + KEGG enrichment + external published-literature concordance)
- An **independent PubMed prior-proposal audit** per drug-cancer association (urologic-oncology-literature-only novelty standard)

## Seven clinical contexts analyzed

**Source-disease contexts** (TCGA Pan-Cancer Atlas cohorts, Master Table 1 rows 1–16):
1. Neuroendocrine prostate cancer (NEPC) — TCGA PRAD n = 494
2. Muscle-invasive bladder cancer (MIBC) — TCGA BLCA n = 411
3. Clear cell renal cell carcinoma (ccRCC) — TCGA KIRC n = 512

**Rare-disease / variant-histology discovery contexts** (published genomic series + GEO discovery-mode, Master Table 1 rows 17–30):

4. Renal medullary carcinoma (RMC) — SMARCB1-deficient
5. Penile squamous cell carcinoma (PSCC)
6. Sarcomatoid urothelial carcinoma
7. Small-cell bladder cancer (SCBC) — lineage-transcription-factor-stratified (ASCL1+, NEUROD1+, POU2F3+, YAP1+)

## Master Table 1 output (30 drug-cancer associations)

Rows 1–16 (source-disease validation) ↔ Rows 17–30 (rare-disease / variant-histology discovery mode).

- **18 previously-proposed** urologic-oncology priorities (convergent literature support)
- **6 framework-novel** within urologic-oncology literature:
  - CXCR1/CXCR2 antagonists (reparixin, navarixin, AZD5069, danirixin, ladarixin) in RMC
  - Anti-CEACAM1 (CM24) in RMC
  - NSD2/WHSC1 inhibition (KTX-1001) in sarcomatoid urothelial carcinoma
  - ATR pathway inhibitors (ceralasertib, berzosertib, elimusertib) in sarcomatoid urothelial carcinoma
  - SSTR2-directed lutetium-177 DOTATATE in NEUROD1+ SCBC
  - CEACAM5-directed targeting in ASCL1+ SCBC (replacement-agent selection required following the December 2023 discontinuation of tusamitamab ravtansine)
- **5 partially novel** variant-specific extensions
- **1 clinically actionable negative biomarker** (TROP2-low in sarcomatoid urothelial carcinoma → sacituzumab govitecan predicted non-response, concordant with Brunelli 2024 / Bahlinger 2024 / Hoffman-Censits 2021)

## Repository layout

```
.
├── README.md                           # this file
├── LICENSE                              # MIT
├── requirements.txt                     # Python dependencies
│
├── code/
│   ├── pipeline/                        # The v26 analytical pipeline (12 numbered scripts)
│   │   ├── 09b_kegg_fetch_fixed.py      # Fetch 18 KEGG pathway gene sets
│   │   ├── 01_rmc_de_analysis.py        # RMC DE
│   │   ├── 03_penile_de_analysis.py     # Penile SCC DE
│   │   ├── 04_sarcomatoid_uc_de.py      # Sarcomatoid UC DE
│   │   ├── 05_scbc_subtype_analysis.py  # SCBC subtype DE (lineage-TF stratified)
│   │   ├── 10_uniform_scoring.py        # KEGG enrichment across all contexts
│   │   ├── 11_master_table_uniform.py   # Build Master Table with uniform 9-point scoring
│   │   └── 12_generate_figures.py       # Generate Figures 1–4
│   └── manuscript_build/                # docx assembly scripts
│
├── data/
│   ├── DE_results/                      # Per-context differential-expression result tables
│   │   ├── FULL_DE_RESULTS_ALL10.csv             # Consolidated DE across all 10 datasets
│   │   ├── GEO_DATASET_AUDIT_10_DATASETS.csv     # 10-dataset audit with PMIDs
│   │   ├── RMC_up_in_null_state.csv              # 13 SMARCB1-loss-driven UP genes (RMC)
│   │   ├── SarcomatoidUC_up.csv                  # SARC vs conventional UC UP genes
│   │   ├── SarcomatoidUC_DE_full.csv.gz          # Full Sarc-UC DE (gzipped)
│   │   ├── SCBC_subtype_calls.csv                # Per-sample lineage TF subtype assignments
│   │   ├── SCBC_up_in_{ASCL1,NEUROD1,POU2F3}.csv # Per-subtype UP genes
│   │   ├── PenileSCC_tumor_up.csv                # Penile SCC tumor-UP genes (filtered)
│   │   └── PenileSCC_DE_full.csv.gz              # Full Penile SCC DE (gzipped)
│   └── ...
│
├── results/
│   ├── MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv  # Central artifact (30 rows × 13 cols)
│   ├── PUBMED_NOVELTY_AUDIT.csv                   # Per-row novelty classification
│   ├── KEGG_PATHWAYS_18.json                      # 18 pre-specified pathway gene sets
│   ├── KEGG_ENRICHMENT_ALL10.json                 # Hypergeometric enrichment per disease (raw)
│   └── KEGG_ENRICHMENT_ALL10.csv                  # Tabular form of KEGG enrichment
│
├── figures/
│   ├── Figure1_pipeline.png                       # Unified pipeline schematic
│   ├── Figure2_RMC.png                            # Renal medullary carcinoma novel findings
│   ├── Figure3_SarcUC.png                         # Sarcomatoid urothelial carcinoma findings
│   └── Figure4_SCBC.png                           # Small-cell bladder cancer (subtype-stratified)
│
└── legacy/v25/                          # Original 3-context source-disease analysis (preserved)
    ├── code/                            # Original v25 analysis scripts
    ├── data/                            # Original v25 DE / KEGG / score CSVs
    └── figures/                         # Original v25 figures
```

## Data sources

- **TCGA Pan-Cancer Atlas 2018** via cBioPortal API: source-disease alteration frequencies
- **Gene Expression Omnibus** (10 accessions): GSE199274, GSE216053, GSE216052, GSE130598, GSE143630, GSE157256, GSE180999, GSE196978, GSE128192, GSE269750
- **KEGG REST API**: 18 pre-specified pathway gene sets
- **Therapeutic Target Database** (accessed May 2026) and **OpenTargets** (release 2026.03): drug-target curation
- **FDA Drugs@FDA**: current approval status (note: drug-approval status as of May 17, 2026 — sacituzumab govitecan accelerated approval in metastatic urothelial carcinoma was voluntarily withdrawn October 2024; tusamitamab ravtansine global development was discontinued by Sanofi December 2023)

## Running the pipeline

```bash
pip install -r requirements.txt

python code/pipeline/09b_kegg_fetch_fixed.py    # Fetch 18 KEGG pathway gene sets
python code/pipeline/01_rmc_de_analysis.py
python code/pipeline/03_penile_de_analysis.py
python code/pipeline/04_sarcomatoid_uc_de.py
python code/pipeline/05_scbc_subtype_analysis.py
python code/pipeline/10_uniform_scoring.py      # KEGG enrichment across all diseases
python code/pipeline/11_master_table_uniform.py # Build Master Table with uniform 9-point scoring
python code/pipeline/12_generate_figures.py     # Generate Figures 1–4
```

Note: scripts use absolute paths reflecting the development environment; adjust for your local setup.

## License

MIT. See [LICENSE](LICENSE).

## How to cite

> Brinkley GJ, Greenberg J, Caso J. A Reproducible Public-Data Pipeline Identifies Convergent and Novel Drug-Repurposing Priorities Across Rare Aggressive Urologic Cancers. Zenodo. 2026. doi:10.5281/zenodo.20217919

The concept-DOI [10.5281/zenodo.20217919](https://doi.org/10.5281/zenodo.20217919) always resolves to the latest version. The v26.0 version-DOI is [10.5281/zenodo.20261995](https://doi.org/10.5281/zenodo.20261995).

(Manuscript citation pending publication acceptance.)

## AI usage disclosure

Claude (Anthropic) and ChatGPT (OpenAI) large-language-model tools were used for coding assistance, literature-audit organization, language editing, and manuscript-structure suggestions. All analyses were executed by author-run Python scripts using publicly available datasets. All PubMed novelty classifications, score component assignments, drug-target interpretations, and final manuscript text were reviewed and approved by the human authors.

## Provenance: `legacy/v25/` (archived, not used by the current manuscript)

The earlier three-context analysis is archived under [`legacy/v25/`](legacy/v25/) for historical provenance only. **It is not the deposit referenced by the v26 manuscript and should not be used to reproduce any v26 claim.** All current reproducibility claims map exclusively to the files at the root of this repository (see the top of this README). The `legacy/v25/` folder contains its own README clarifying its archive status.

## Contact

For questions about reproducibility or methodology, open an issue on GitHub or contact the corresponding author.
