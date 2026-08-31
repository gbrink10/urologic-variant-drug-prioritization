"""RMC drug-target identification from GSE180999.

Author-supplied DE results in GSE180999_DE.xlsx have two sheets:
  - RMC2C+SMARCB1: SMARCB1-rescue vs NEG (SMARCB1-null) in RMC-2C cell line
  - RMC219+SMARCB1: SMARCB1-rescue vs NEG (SMARCB1-null) in RMC219 cell line

DIRECTION: "treated vs NEG" with treated = SMARCB1-restored. Therefore:
  Log2FC < 0 in 48h_vs_NEG = gene went DOWN upon SMARCB1 restoration
                         = gene was UP in the SMARCB1-null state
                         = candidate UP in RMC tumor biology
                         = potential pharmacologic target

We require:
  - 48h adjusted p-value < 0.05 in BOTH cell lines (FDR-controlled)
  - 48h Log2FC ≤ -1.0 in BOTH cell lines (consistent across models)
  - Optional check: 12h directionally consistent

Output: ranked list of SMARCB1-loss-driven genes (candidate drug targets),
with concordance information across both cell lines.

SUPERSEDED (v29). This script produced the v26-v28 analysis and is retained so
that earlier versions of the manuscript remain reconstructible. It is NOT part
of the current pipeline. The v29 analysis refits every dataset with design-aware
models and recomputes the scores from the fitted tables:

    32_prepare_matrices.py  ->  33_refit_limma.R  ->  35/36 enrichment
    38_extract_row_definitions.py  ->  39_rescore_from_refit.py
    41_candidate_selection.py

"""
import sys
from pathlib import Path

import paths
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')

DATA = paths.RAW / 'GSE180999' / 'GSE180999_rnaseq_rmc_cell_lines_differential_expression.xlsx'
RESULTS = paths.RESULTS
RESULTS.mkdir(parents=True, exist_ok=True)

# Load both sheets
xl = pd.ExcelFile(DATA)
rmc2c = xl.parse('RMC2C+SMARCB1').rename(columns={
    'Gene name': 'gene',
    'Log2 FC (12h_vs_NEG)': 'l2fc_12h_RMC2C',
    'Adjusted p-value (12h_vs_NEG)': 'qval_12h_RMC2C',
    'Log2 FC (48h_vs_NEG)': 'l2fc_48h_RMC2C',
    'Adjusted p-value (48h_vs_NEG)': 'qval_48h_RMC2C',
})
rmc219 = xl.parse('RMC219+SMARCB1').rename(columns={
    'Gene name': 'gene',
    'Log2 FC (12h_vs_NEG)': 'l2fc_12h_RMC219',
    'Adjusted p-value (12h_vs_NEG)': 'qval_12h_RMC219',
    'Log2 FC (48h_vs_NEG)': 'l2fc_48h_RMC219',
    'Adjusted p-value (48h_vs_NEG)': 'qval_48h_RMC219',
})

print(f"RMC-2C DE table: {len(rmc2c):,} genes")
print(f"RMC219 DE table: {len(rmc219):,} genes")

# Merge on gene
de = pd.merge(rmc2c, rmc219, on='gene', how='inner')
print(f"Joined (genes in both): {len(de):,}")

# Drop rows with any NaN in 48h columns
de = de.dropna(subset=['l2fc_48h_RMC2C', 'qval_48h_RMC2C',
                       'l2fc_48h_RMC219', 'qval_48h_RMC219']).copy()
print(f"After dropping NaN 48h: {len(de):,}")

# ----------------------------------------------------------
# Criterion 1: UP in RMC null state = DOWN upon SMARCB1 rescue at 48h
#   Threshold: l2fc_48h ≤ -1.0 AND qval_48h < 0.05 in BOTH cell lines
# ----------------------------------------------------------
up_in_RMC = de[
    (de['l2fc_48h_RMC2C'] <= -1.0) & (de['qval_48h_RMC2C'] < 0.05) &
    (de['l2fc_48h_RMC219'] <= -1.0) & (de['qval_48h_RMC219'] < 0.05)
].copy()
up_in_RMC['mean_l2fc_48h'] = (up_in_RMC['l2fc_48h_RMC2C'] +
                               up_in_RMC['l2fc_48h_RMC219']) / 2
up_in_RMC = up_in_RMC.sort_values('mean_l2fc_48h').reset_index(drop=True)

print(f"\n{'='*70}")
print(f"GENES UP IN RMC (SMARCB1-null state), CONSISTENT ACROSS BOTH CELL LINES")
print(f"  Criteria: 48h_vs_NEG Log2FC ≤ -1.0 AND adj-p < 0.05 in BOTH RMC-2C AND RMC219")
print(f"  Total: {len(up_in_RMC)} genes")
print(f"{'='*70}")
print(f"\nTop 50 genes most strongly UP in RMC (most negative mean Log2FC = strongest "
      f"rescue-induced suppression = strongest SMARCB1-loss-driven elevation):")
print()
print(f"{'Rank':<5}{'Gene':<14}{'l2FC_RMC2C':<12}{'l2FC_RMC219':<13}{'mean_l2FC':<11}"
      f"{'q_RMC2C':<11}{'q_RMC219':<11}")
print("-" * 80)
for i, row in up_in_RMC.head(50).iterrows():
    print(f"{i+1:<5}{row['gene']:<14}{row['l2fc_48h_RMC2C']:<12.2f}"
          f"{row['l2fc_48h_RMC219']:<13.2f}{row['mean_l2fc_48h']:<11.2f}"
          f"{row['qval_48h_RMC2C']:<11.2e}{row['qval_48h_RMC219']:<11.2e}")

# Save
up_in_RMC.to_csv(RESULTS / 'RMC_up_in_null_state.csv', index=False)
print(f"\nSaved → {RESULTS / 'RMC_up_in_null_state.csv'}")

# ----------------------------------------------------------
# Also produce DOWN in RMC null = UP upon SMARCB1 rescue
# (for context — these are genes SUPPRESSED in the tumor that
#  could be reactivated as a therapeutic strategy)
# ----------------------------------------------------------
down_in_RMC = de[
    (de['l2fc_48h_RMC2C'] >= 1.0) & (de['qval_48h_RMC2C'] < 0.05) &
    (de['l2fc_48h_RMC219'] >= 1.0) & (de['qval_48h_RMC219'] < 0.05)
].copy()
down_in_RMC['mean_l2fc_48h'] = (down_in_RMC['l2fc_48h_RMC2C'] +
                                 down_in_RMC['l2fc_48h_RMC219']) / 2
down_in_RMC = down_in_RMC.sort_values('mean_l2fc_48h', ascending=False).reset_index(drop=True)
print(f"\nGenes DOWN in RMC (UP upon SMARCB1 rescue) — for context, {len(down_in_RMC)} total")
print(f"Top 20 genes most strongly DOWN in RMC:")
print()
print(f"{'Rank':<5}{'Gene':<14}{'mean_l2FC':<11}")
for i, row in down_in_RMC.head(20).iterrows():
    print(f"{i+1:<5}{row['gene']:<14}{row['mean_l2fc_48h']:<11.2f}")
down_in_RMC.to_csv(RESULTS / 'RMC_down_in_null_state.csv', index=False)

print(f"\nDone. Files saved to {RESULTS}")
