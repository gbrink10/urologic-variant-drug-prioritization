"""Compute drug evidence scores for v12 per the methodology agreed in the comments-response document.

Scoring formula (0-10 composite):
  TCGA/Genomic evidence:       0-3 points
  GEO transcriptomic evidence: 0-3 points
  KEGG pathway enrichment:     0-2 points
  External literature:         0-1 point
  Phase III validation:        0-1 point

Sources for evidence:
  - FULL_DE_RESULTS.csv (Welch t-test log2FC + p-values across 5 DE comparisons)
  - KEGG_ENRICHMENT.csv (hypergeometric test ORs)
  - Manual: TCGA alteration frequencies (verified via cBioPortal API, 2026-05-13)
  - Manual: external literature, Phase III status
"""
import csv
import pandas as pd
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

VALIDATION_DIR = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")

# Load data
de = pd.read_csv(VALIDATION_DIR / "FULL_DE_RESULTS.csv")
print(f"Loaded {len(de):,} DE results from FULL_DE_RESULTS.csv")

# Define drug-cancer pairs with scoring inputs
drugs = [
    # NEPC
    dict(cancer="NEPC", drug="Venetoclax", target="BCL2 (apoptosis)",
         tcga_evidence="RB1 loss 85–92% in NEPC series (refs 13,14)", tcga_score=3,
         geo_evidence="BCL2 TPM=34.3 + RB1 TPM=2.7 (PM154 baseline, GSE216053); PARP1 TPM=267 also high (synthetic-lethality combo rationale)", geo_score=3,
         kegg_evidence="Apoptosis/BCL2 OR=1.76, p=0.12 (trend, ns)", kegg_score=0,
         ext_evidence="Beltran 2016 NEPC; Zellweger 2005 Bcl-2 11% CRPC", ext_score=1,
         phase3="Pending; NEPC variant trials limited", phase3_score=0),
    dict(cancer="NEPC", drug="Alisertib‡", target="AURKA (mitotic kinase)",
         tcga_evidence="AURKA reported elevated in NEPC series", tcga_score=2,
         geo_evidence="CXCR7 KD → AURKA log2FC=-1.17 (trend p=0.10); MYCN TPM=92 PM154; Cell Cycle KEGG OR=2.86 (GSE199274)", geo_score=2,
         kegg_evidence="Cell Cycle OR=2.86, p=0.0002 (MDVr cells)", kegg_score=2,
         ext_evidence="Gritsina CXCR7/AURKA 2023; N-myc/Aurora-A axis (Beltran)", ext_score=1,
         phase3="Beltran Phase II NEPC 2019 (signal of response)", phase3_score=0),
    dict(cancer="NEPC", drug="Tazemetostat", target="EZH2 (polycomb)",
         tcga_evidence="EZH2 reported overexpressed in NEPC series", tcga_score=2,
         geo_evidence="EZH2 TPM=39.7 (PM154); DNMT3A KO reduces EZH2 (log2FC=-0.61)", geo_score=2,
         kegg_evidence="N/A — EZH2 not in pre-specified KEGG pathways tested", kegg_score=0,
         ext_evidence="Beltran NEPC reprogramming; Aggarwal 2018", ext_score=1,
         phase3="None for NEPC; Phase II ongoing CRPC", phase3_score=0),
    dict(cancer="NEPC", drug="Decitabine", target="DNMT1/3A (methylation)",
         tcga_evidence="DNMT elevated in NEPC", tcga_score=2,
         geo_evidence="DNMT1 TPM=123.6 (very high); DNMT1 KO restores RB1 (log2FC=+0.70, GSE216052)", geo_score=3,
         kegg_evidence="N/A — DNA methylation not in KEGG panel", kegg_score=0,
         ext_evidence="Beltran NEPC DNMT involvement", ext_score=1,
         phase3="None for NEPC", phase3_score=0),
    dict(cancer="NEPC", drug="Cabazitaxel+carboplatin", target="TP53 (platinum-sensitive)",
         tcga_evidence="Near-universal TP53 alteration in NEPC (refs 13,14)", tcga_score=3,
         geo_evidence="TP53 TPM=43.2 (PM154; high baseline); no specific DE", geo_score=0,
         kegg_evidence="p53 Signaling OR=2.28, p=0.021 (MDVr)", kegg_score=1,
         ext_evidence="Aparicio 2013 platinum sensitivity NEPC", ext_score=1,
         phase3="Off-label standard for variant prostate cancer", phase3_score=1),
    # Newly added based on PARP analysis:
    dict(cancer="NEPC", drug="Olaparib (NEW)", target="PARP1/2 (synthetic lethality)",
         tcga_evidence="RB1-loss biology; BRCA/HRR co-occurrence in advanced PCa ~10–20%", tcga_score=2,
         geo_evidence="PARP1 TPM=267 + PARP2 TPM=45 (PM154 baseline; both highly expressed)", geo_score=2,
         kegg_evidence="Homologous Recombination OR=1.62, p=0.16 (trend, ns)", kegg_score=0,
         ext_evidence="PROfound trial in BRCA/ATM CRPC; synthetic lethality literature", ext_score=1,
         phase3="PROfound (olaparib mCRPC HRR+); none for NEPC specifically", phase3_score=1),
    # MIBC
    dict(cancer="MIBC", drug="Alisertib‡", target="AURKA/AURKB",
         tcga_evidence="AURKA mRNA elevated TCGA-BLCA; high-level amp 0.2%", tcga_score=1,
         geo_evidence="AURKB log2FC=+4.08, AURKA +2.58 (p<0.001); TTK, PLK4, PBK, CDK1, CHEK1 all upregulated", geo_score=3,
         kegg_evidence="Cell Cycle panel OR=1.63, p=0.028", kegg_score=1,
         ext_evidence="Burgess MIBC AURKA-OS HR=6.10, p<0.001", ext_score=1,
         phase3="None for AURKA in MIBC", phase3_score=0),
    dict(cancer="MIBC", drug="Talazoparib", target="PARP1/2 (HR-deficiency biomarker: ERCC2/ATM)",
         tcga_evidence="ERCC2 9%, ATM 13% mutations (TCGA-BLCA)", tcga_score=2,
         geo_evidence="ATR log2FC=+0.55, p=0.038; PRKDC +1.38, p=0.019", geo_score=1,
         kegg_evidence="HR pathway not significantly enriched", kegg_score=0,
         ext_evidence="PARP literature in HR-deficient tumors", ext_score=1,
         phase3="BAYOU durvalumab+olaparib mixed; mUC trials ongoing", phase3_score=0),
    dict(cancer="MIBC", drug="Alpelisib", target="PIK3CA (α-isoform)",
         tcga_evidence="PIK3CA 22% activating mutations (TCGA-BLCA)", tcga_score=2,
         geo_evidence="ERBB2/ERBB3 upregulated (log2FC=+2.09/+1.87) suggesting RTK-PI3K signaling", geo_score=1,
         kegg_evidence="PI3K-AKT panel-restricted: no significant enrichment", kegg_score=0,
         ext_evidence="PIK3CA biology established (SOLAR-1 breast)", ext_score=1,
         phase3="None for MIBC", phase3_score=0),
    dict(cancer="MIBC", drug="Erdafitinib", target="FGFR2/3",
         tcga_evidence="FGFR3 19% alterations (TCGA-BLCA)", tcga_score=2,
         geo_evidence="FGFR3 log2FC=+1.63, p=0.016 (significant)", geo_score=2,
         kegg_evidence="N/A — direct target measurement", kegg_score=0,
         ext_evidence="BLC2001 (Loriot 2019)", ext_score=1,
         phase3="THOR phase III positive (Loriot 2023)", phase3_score=1),
    dict(cancer="MIBC", drug="Enfortumab Vedotin", target="NECTIN4 (ADC)",
         tcga_evidence="Near-universal NECTIN4 expression in urothelial (>80% IHC)", tcga_score=3,
         geo_evidence="Near-universal NECTIN4 expression (TCGA/published)", geo_score=3,
         kegg_evidence="N/A", kegg_score=0,
         ext_evidence="EV-201, EV-103 cohort K, EV-302", ext_score=1,
         phase3="KEYNOTE-905/EV-303 + EV-302 both positive", phase3_score=1),
    dict(cancer="MIBC", drug="Pembrolizumab", target="PD-1 / TMB-H",
         tcga_evidence="TMB-H 26% in BLCA (≥10 mut/Mb)", tcga_score=2,
         geo_evidence="Immune-checkpoint biology; gene-level signal limited in panel", geo_score=1,
         kegg_evidence="N/A", kegg_score=0,
         ext_evidence="KEYNOTE-045, -057, -361 (multiple)", ext_score=1,
         phase3="KEYNOTE-905/EV-303 + KEYNOTE-045 + EV-302", phase3_score=1),
    dict(cancer="MIBC", drug="Palbociclib", target="CDK4/6",
         tcga_evidence="CDKN2A 32% deep deletion (releases CDK4/6 from inhibition)", tcga_score=2,
         geo_evidence="CDK1 +3.59, CDK2 +0.92 (proliferative); CDK4/6 not directly upregulated", geo_score=1,
         kegg_evidence="Cell Cycle OR=1.63, p=0.028 (panel-restricted)", kegg_score=1,
         ext_evidence="CDK4/6i biology in CDKN2A-loss settings", ext_score=1,
         phase3="None for MIBC", phase3_score=0),
    # sRCC
    dict(cancer="ccRCC/sRCC", drug="Pazopanib", target="VEGFR/PDGFR",
         tcga_evidence="VHL 34% mut/CNA (≥50% with hypermethylation; ref 10)", tcga_score=2,
         geo_evidence="VEGFA rank 30/57,353 (top 0.05%); KDR rank 412 (top 0.72%)", geo_score=3,
         kegg_evidence="VEGF/HIF constitutively active across ccRCC stages", kegg_score=1,
         ext_evidence="COMPARZ, multiple RCC trials", ext_score=1,
         phase3="COMPARZ (Motzer); standard of care for adv RCC", phase3_score=1),
    dict(cancer="ccRCC/sRCC", drug="Belzutifan", target="HIF2α / EPAS1",
         tcga_evidence="VHL 34% mut/CNA (≥50% with hypermethylation)", tcga_score=2,
         geo_evidence="EPAS1 rank 75/57,353 (top 0.13%); upregulated in HLRCC p=0.003", geo_score=3,
         kegg_evidence="HIF-1 pathway annotation", kegg_score=1,
         ext_evidence="LITESPARK-001 (Jonasch VHL)", ext_score=1,
         phase3="LITESPARK-005 positive (Choueiri 2024)", phase3_score=1),
    dict(cancer="ccRCC", drug="Abemaciclib", target="CDK4/6",
         tcga_evidence="CDKN2A deep del 3% in KIRC (rare)", tcga_score=0,
         geo_evidence="CDK4 rank top 8.2% (detectable); not differentially upregulated", geo_score=1,
         kegg_evidence="Not enriched", kegg_score=0,
         ext_evidence="Limited RCC-specific data", ext_score=0,
         phase3="None for RCC", phase3_score=0),
]

# Compute totals
for d in drugs:
    d['total'] = d['tcga_score'] + d['geo_score'] + d['kegg_score'] + d['ext_score'] + d['phase3_score']
    d['tier'] = ("Strong" if d['total'] >= 7 else
                 "Moderate" if d['total'] >= 4 else
                 "Exploratory")

# Output: print + save
print("\n" + "=" * 110)
print(f"{'Cancer':<14}{'Drug':<28}{'Target':<35}{'TCGA':>5}{'GEO':>5}{'KEGG':>5}{'Ext':>5}{'PhIII':>6}{'Tot':>5}{'Tier':>14}")
print("=" * 110)
for d in drugs:
    print(f"{d['cancer']:<14}{d['drug']:<28}{d['target'][:34]:<35}"
          f"{d['tcga_score']:>5}{d['geo_score']:>5}{d['kegg_score']:>5}{d['ext_score']:>5}"
          f"{d['phase3_score']:>6}{d['total']:>5}/10{d['tier']:>13}")
print()

# Save CSV (Supplementary Data 4)
out_csv = VALIDATION_DIR / "DRUG_EVIDENCE_SCORES_v12.csv"
with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['cancer', 'drug', 'target', 'tcga_evidence', 'tcga_score',
                  'geo_evidence', 'geo_score', 'kegg_evidence', 'kegg_score',
                  'ext_evidence', 'ext_score', 'phase3', 'phase3_score',
                  'total', 'tier']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for d in drugs:
        w.writerow(d)
print(f"Saved: {out_csv}")
