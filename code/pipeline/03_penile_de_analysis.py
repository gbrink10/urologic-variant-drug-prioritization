"""Penile SCC DE analysis from GSE196978.

22 samples = 6 Normal penis + 16 Penile carcinoma.
Platform: Affymetrix HTA 2.0 (GPL17586) — Transcript Cluster ID format.

Steps:
1. Build expression matrix from individual sample tables (already log2-normalized).
2. Download GPL17586 annotation to map TC IDs → gene symbols.
3. Two-sample t-test tumor vs normal per probe.
4. BH-FDR correct.
5. Filter for tumor-UP genes (log2FC > 0.5, q<0.05).
6. Save ranked candidate drug-target list.
"""
import sys, os
from pathlib import Path
import GEOparse
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
sys.stdout.reconfigure(encoding='utf-8')

DATA = Path(r"C:\Users\garre\framework_expansion\data")
RESULTS = Path(r"C:\Users\garre\framework_expansion\results")
os.chdir(DATA)

print("=" * 70)
print("Penile SCC DE Analysis: GSE196978 (6 Normal vs 16 Cancer)")
print("=" * 70)

# Load dataset
gse = GEOparse.get_GEO(geo='GSE196978', destdir='.', silent=True)
print(f"Samples: {len(gse.gsms)}")

# Build sample groups
sample_groups = {}
for gsm_id, gsm in gse.gsms.items():
    chars = gsm.metadata.get('characteristics_ch1', [])
    state = None
    for c in chars:
        if 'disease state:' in c.lower():
            state = c.split(':', 1)[1].strip()
            break
    sample_groups[gsm_id] = 'normal' if 'Normal' in (state or '') else 'cancer'
groups = pd.Series(sample_groups, name='group')
print(f"  Normal: {(groups=='normal').sum()}")
print(f"  Cancer: {(groups=='cancer').sum()}")

# Build expression matrix from sample tables
print("\nBuilding expression matrix...")
expr_data = {}
for gsm_id, gsm in gse.gsms.items():
    tbl = gsm.table  # ID_REF, VALUE
    s = pd.Series(tbl['VALUE'].values, index=tbl['ID_REF'].values, name=gsm_id)
    expr_data[gsm_id] = s
expr = pd.DataFrame(expr_data)
print(f"  Expression matrix: {expr.shape[0]:,} probes × {expr.shape[1]} samples")

# Coerce to numeric (some columns may have mixed types per the warning)
expr = expr.apply(pd.to_numeric, errors='coerce').dropna()
print(f"  After numeric coercion + dropna: {expr.shape}")

# Get gene symbol annotation from platform GPL17586
print("\nFetching GPL17586 platform annotation...")
gpl = GEOparse.get_GEO(geo='GPL17586', destdir='.', silent=True)
ann = gpl.table
print(f"  Annotation rows: {len(ann):,}")
print(f"  Annotation columns: {list(ann.columns)[:10]}")

# Find the gene symbol column
gene_col = None
for c in ann.columns:
    if c.lower() in ('gene_symbol', 'gene symbol', 'symbol', 'gene_assignment'):
        gene_col = c
        break
if gene_col is None:
    # Print first few rows to find it manually
    print(f"\n  Sample annotation rows:")
    print(ann.head(3).to_string(max_colwidth=80))
print(f"  Using gene column: {gene_col}")

# Run DE: t-test tumor vs normal per probe
print("\nRunning DE (Welch's t-test) per probe...")
tumor_samples = groups[groups == 'cancer'].index.tolist()
normal_samples = groups[groups == 'normal'].index.tolist()

tumor_expr = expr[tumor_samples]
normal_expr = expr[normal_samples]

stat_vals, p_vals = stats.ttest_ind(tumor_expr.values, normal_expr.values, axis=1, equal_var=False)

# Log2FC = mean(tumor) - mean(normal); data is already log2-normalized
l2fc = tumor_expr.mean(axis=1) - normal_expr.mean(axis=1)

de_results = pd.DataFrame({
    'probe_id': expr.index,
    'log2fc': l2fc.values,
    't_stat': stat_vals,
    'pvalue': p_vals,
})
de_results = de_results.dropna()
de_results['qvalue'] = multipletests(de_results['pvalue'], method='fdr_bh')[1]
print(f"  Tested {len(de_results):,} probes")
print(f"  Probes with q<0.05: {(de_results['qvalue']<0.05).sum():,}")
print(f"  Probes with q<0.05 AND |log2FC|>1: {((de_results['qvalue']<0.05) & (de_results['log2fc'].abs()>1)).sum():,}")

# Add gene-symbol annotation
if gene_col is not None:
    ann_df = ann.set_index('ID')[gene_col] if 'ID' in ann.columns else ann.set_index(ann.columns[0])[gene_col]
    de_results['gene'] = de_results['probe_id'].map(ann_df)
else:
    de_results['gene'] = None

# Filter for top tumor-UP genes (consistent with framework: drug-target candidates)
tumor_up = de_results[(de_results['log2fc'] > 1.0) & (de_results['qvalue'] < 0.05)].copy()
tumor_up = tumor_up.sort_values('log2fc', ascending=False).reset_index(drop=True)

print(f"\nTop 30 genes UP in penile cancer (log2FC>1, q<0.05):")
print(f"{'Rank':<5}{'Probe':<20}{'Gene':<25}{'log2FC':<10}{'pvalue':<12}{'qvalue':<12}")
print('-' * 90)
for i, row in tumor_up.head(30).iterrows():
    gene_str = str(row.get('gene', ''))[:24]
    print(f"{i+1:<5}{str(row['probe_id'])[:19]:<20}{gene_str:<25}{row['log2fc']:<10.2f}{row['pvalue']:<12.2e}{row['qvalue']:<12.2e}")

# Save
de_results.to_csv(RESULTS / 'PenileSCC_DE_full.csv', index=False)
tumor_up.to_csv(RESULTS / 'PenileSCC_tumor_up.csv', index=False)
print(f"\nSaved DE table and tumor-UP genes → {RESULTS}")
