"""SCBC subtype-stratified analysis from GSE269750.

44 SCBC samples; no normal control. The Yu/Hardin 2024 paper classified SCBC
into lineage-TF subtypes (ASCL1+, NEUROD1+, POU2F3+) analogous to SCLC.

Plan:
1. Load batch-adjusted normalized expression matrix.
2. Classify each sample by lineage TF expression (max of ASCL1, NEUROD1, POU2F3).
3. Run DE per subtype vs the others.
4. Identify subtype-specific drug-target candidates.

SUPERSEDED (v29). This script produced the v26-v28 analysis and is retained so
that earlier versions of the manuscript remain reconstructible. It is NOT part
of the current pipeline. The v29 analysis refits every dataset with design-aware
models and recomputes the scores from the fitted tables:

    32_prepare_matrices.py  ->  33_refit_limma.R  ->  35/36 enrichment
    38_extract_row_definitions.py  ->  39_rescore_from_refit.py
    41_candidate_selection.py

"""
import sys, gzip
from pathlib import Path

import paths
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
sys.stdout.reconfigure(encoding='utf-8')

DATA = paths.RAW / 'GSE269750' / 'GSE269750_SCBC_after_batch_adjusting_after_normalization_2024_01_24.txt.gz'
RESULTS = paths.RESULTS

print("=" * 70)
print("SCBC subtype-stratified analysis: GSE269750")
print("=" * 70)

# Load expression matrix
with gzip.open(DATA, 'rt') as f:
    expr = pd.read_csv(f, sep='\t', index_col=0)
print(f"Expression matrix: {expr.shape}")
print(f"First 5 samples: {list(expr.columns)[:5]}")
print(f"First 5 genes: {list(expr.index)[:5]}")

# Lineage TF subtype calls
lineage_tfs = ['ASCL1', 'NEUROD1', 'POU2F3', 'YAP1']
print(f"\nLineage TF expression per sample:")
tf_expr = pd.DataFrame()
for tf in lineage_tfs:
    if tf in expr.index:
        tf_expr[tf] = expr.loc[tf]
    else:
        print(f"  ! {tf} not in expression matrix")
print(tf_expr.head(8).round(2))

# Assign subtype: highest-expressing lineage TF per sample
tf_expr['subtype'] = tf_expr.idxmax(axis=1)
print(f"\nSubtype counts:")
print(tf_expr['subtype'].value_counts())

# Save the subtype calls
tf_expr.to_csv(RESULTS / 'SCBC_subtype_calls.csv')

# DE per subtype: subtype vs all others
print(f"\n{'='*70}")
print(f"DE: each subtype vs all others")
print(f"{'='*70}")

subtype_results = {}
for subtype in tf_expr['subtype'].unique():
    if pd.isna(subtype): continue
    in_subtype = tf_expr.index[tf_expr['subtype'] == subtype].tolist()
    other = tf_expr.index[tf_expr['subtype'] != subtype].tolist()
    in_subtype = [s for s in in_subtype if s in expr.columns]
    other = [s for s in other if s in expr.columns]
    if len(in_subtype) < 3 or len(other) < 3:
        print(f"\n{subtype} (n={len(in_subtype)}) — too few samples; skipping")
        continue

    expr_in = expr[in_subtype]
    expr_other = expr[other]

    # Mask: only genes with variance
    mask = (expr_in.std(axis=1) > 0) | (expr_other.std(axis=1) > 0)
    expr_in_f = expr_in[mask]
    expr_other_f = expr_other[mask]

    stat_vals, p_vals = stats.ttest_ind(expr_in_f.values, expr_other_f.values, axis=1, equal_var=False)
    l2fc = expr_in_f.mean(axis=1) - expr_other_f.mean(axis=1)

    de = pd.DataFrame({
        'gene': expr_in_f.index,
        'log2fc': l2fc.values,
        'pvalue': p_vals,
    }).dropna()
    de['qvalue'] = multipletests(de['pvalue'], method='fdr_bh')[1]

    up = de[(de['log2fc'] > 1.0) & (de['qvalue'] < 0.05)].sort_values('log2fc', ascending=False)
    print(f"\n{subtype} ({len(in_subtype)} samples vs {len(other)} other):")
    print(f"  {len(up)} genes UP at log2FC>1, q<0.05")
    print(f"  Top 20:")
    for i, row in up.head(20).reset_index(drop=True).iterrows():
        print(f"    {i+1:>3}. {row['gene']:<14} log2FC={row['log2fc']:.2f}  q={row['qvalue']:.2e}")

    up.to_csv(RESULTS / f'SCBC_up_in_{subtype}.csv', index=False)
    subtype_results[subtype] = up

print(f"\nSaved subtype-specific UP gene tables to {RESULTS}")
