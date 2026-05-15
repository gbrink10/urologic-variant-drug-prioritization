"""Recompute drug evidence scores on a 9-point molecular-only basis (Phase III removed).

The 10-point evidence score is replaced by:
  - 9-point molecular prioritization score (TCGA 0-3 + GEO 0-3 + KEGG 0-2 + External lit 0-1)
  - Phase III concordance reported separately as a binary flag + trial citation

Tier cutoffs (proportional to original): Strong ≥7, Moderate 4-6, Exploratory ≤3.

Output: DRUG_EVIDENCE_SCORES_v18.csv
"""
import csv
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

VAL = Path(r"C:\Users\garre\OneDrive\Books_Uro\Desktop\VALIDATION_PACKAGE_Bladder_Cancer_Study")
OUT = VAL / "DRUG_EVIDENCE_SCORES_v18.csv"

# Re-derive from v12 scores but drop Phase III component
drugs = [
    # (cancer, drug, target, tcga, geo, kegg, ext, ph3_concordance, ph3_trial)
    ("NEPC", "Venetoclax", "BCL2", 3, 3, 0, 1, "", ""),
    ("NEPC", "Alisertib‡", "AURKA", 2, 2, 2, 1, "", ""),
    ("NEPC", "Tazemetostat", "EZH2", 2, 2, 0, 1, "", ""),
    ("NEPC", "Decitabine", "DNMT1/3A", 2, 3, 0, 1, "", ""),
    ("NEPC", "Cabazitaxel+carboplatin", "TP53/platinum-sensitive", 3, 0, 1, 1, "Yes (off-label SOC)", "Aparicio 2013 J Clin Oncol"),
    ("NEPC", "Olaparib", "PARP1/2", 2, 2, 0, 1, "Yes (mCRPC HRR+)", "PROfound (de Bono NEJM 2020)"),
    ("MIBC", "Alisertib‡", "AURKA/AURKB", 1, 3, 1, 1, "", ""),
    ("MIBC", "Talazoparib", "PARP1/2", 2, 1, 0, 1, "", ""),
    ("MIBC", "Alpelisib", "PIK3CA", 2, 1, 0, 1, "", ""),
    ("MIBC", "Erdafitinib", "FGFR2/3", 2, 2, 0, 1, "Yes (mUC)", "THOR (Loriot NEJM 2023)"),
    ("MIBC", "Enfortumab Vedotin", "NECTIN4", 3, 3, 0, 1, "Yes (1L UC; perioperative MIBC)", "EV-302 (Powles NEJM 2024); KEYNOTE-905/EV-303 (Vulsteke NEJM 2026)"),
    ("MIBC", "Pembrolizumab", "PD-1/TMB-H", 2, 1, 0, 1, "Yes (1L UC; perioperative MIBC)", "EV-302; KEYNOTE-905/EV-303"),
    ("MIBC", "Palbociclib", "CDK4/6", 2, 1, 1, 1, "", ""),
    ("ccRCC/sRCC", "Pazopanib", "VEGFR/PDGFR", 2, 3, 1, 1, "Yes (adv RCC)", "COMPARZ (Motzer NEJM 2013)"),
    ("ccRCC/sRCC", "Belzutifan", "HIF2α/EPAS1", 2, 3, 1, 1, "Yes (adv ccRCC; VHL-RCC)", "LITESPARK-005 (Choueiri NEJM 2024); Motzer NEJM 2021 (VHL)"),
    ("ccRCC", "Abemaciclib", "CDK4/6", 0, 1, 0, 0, "", ""),
]

rows = []
for cancer, drug, target, tcga, geo, kegg, ext, ph3, ph3_trial in drugs:
    score = tcga + geo + kegg + ext
    tier = "Strong" if score >= 7 else ("Moderate" if score >= 4 else "Exploratory")
    rows.append({
        "cancer": cancer, "drug": drug, "target": target,
        "tcga_score": tcga, "geo_score": geo, "kegg_score": kegg, "ext_score": ext,
        "score": score, "tier": tier,
        "phase3_concordance": ph3, "phase3_trial": ph3_trial,
    })

# Print summary
print(f"{'Cancer':<14}{'Drug':<28}{'TCGA':>5}{'GEO':>5}{'KEGG':>5}{'Ext':>5}{'Score':>7}{'Tier':>14}{'PhIII':>8}")
print("=" * 100)
for r in rows:
    print(f"{r['cancer']:<14}{r['drug']:<28}{r['tcga_score']:>5}{r['geo_score']:>5}"
          f"{r['kegg_score']:>5}{r['ext_score']:>5}{r['score']:>5}/9{r['tier']:>14}"
          f"{'  ✓' if r['phase3_concordance'] else '  —':>8}")

# Save CSV
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    fieldnames = ["cancer", "drug", "target", "tcga_score", "geo_score", "kegg_score", "ext_score",
                  "score", "tier", "phase3_concordance", "phase3_trial"]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"\nSaved: {OUT}")
