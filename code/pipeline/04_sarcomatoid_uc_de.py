"""Sarcomatoid urothelial carcinoma DE analysis from GSE128192.

112 samples: 84 conventional UC + 28 SARC (sarcomatoid).
Platform: Illumina HumanHT-12 V4 (GPL14951).

Comparison: SARC vs UC (variant histology vs source disease).
Goal: Identify drug targets specifically upregulated in sarcomatoid variant.

SUPERSEDED (v29). This script produced the v26-v28 analysis and is retained so
that earlier versions of the manuscript remain reconstructible. It is NOT part
of the current pipeline. The v29 analysis refits every dataset with design-aware
models and recomputes the scores from the fitted tables:

    32_prepare_matrices.py  ->  33_refit_limma.R  ->  35/36 enrichment
    38_extract_row_definitions.py  ->  39_rescore_from_refit.py
    41_candidate_selection.py

"""
import sys, os, re
from pathlib import Path

import paths
import GEOparse
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
sys.stdout.reconfigure(encoding='utf-8')

DATA = paths.DATA
RESULTS = paths.RESULTS
os.chdir(DATA)

print("=" * 70)
print("Sarcomatoid UC DE Analysis: GSE128192 (28 SARC vs 84 UC)")
print("=" * 70)

gse = GEOparse.get_GEO(geo='GSE128192', destdir='.', silent=True)

# Build sample groups from title prefix
sample_groups = {}
for gsm_id, gsm in gse.gsms.items():
    title = gsm.metadata.get('title', [''])[0]
    m = re.match(r'^([A-Za-z]+)', title)
    prefix = m.group(1) if m else ''
    sample_groups[gsm_id] = 'sarc' if prefix == 'SARC' else 'uc'

groups = pd.Series(sample_groups, name='group')
print(f"  SARC: {(groups=='sarc').sum()}")
print(f"  UC: {(groups=='uc').sum()}")

# Build expression matrix
print("\nBuilding expression matrix...")
expr_data = {}
for gsm_id, gsm in gse.gsms.items():
    tbl = gsm.table
    expr_data[gsm_id] = pd.Series(tbl['VALUE'].values, index=tbl['ID_REF'].values)
expr = pd.DataFrame(expr_data)
expr = expr.apply(pd.to_numeric, errors='coerce').dropna()
print(f"  Matrix: {expr.shape}")

# Platform annotation for Illumina HT-12 V4 (GPL14951)
print("\nFetching GPL14951 platform annotation...")
gpl = GEOparse.get_GEO(geo='GPL14951', destdir='.', silent=True)
ann = gpl.table
print(f"  Annotation columns: {list(ann.columns)[:15]}")

# Find probe-id and symbol columns
id_col = 'ID' if 'ID' in ann.columns else ann.columns[0]
sym_col = None
for c in ann.columns:
    if c.lower() in ('symbol', 'gene symbol', 'genesymbol', 'ilmn_symbol'):
        sym_col = c; break
if sym_col is None:
    for c in ann.columns:
        if 'symbol' in c.lower():
            sym_col = c; break
print(f"  Using {id_col}=probe, {sym_col}=symbol")

probe2gene = ann.set_index(id_col)[sym_col].to_dict() if sym_col else {}

# DE
print("\nRunning Welch's t-test SARC vs UC per probe...")
sarc_samples = groups[groups == 'sarc'].index.tolist()
uc_samples = groups[groups == 'uc'].index.tolist()

stat_vals, p_vals = stats.ttest_ind(expr[sarc_samples].values, expr[uc_samples].values, axis=1, equal_var=False)
l2fc = expr[sarc_samples].mean(axis=1) - expr[uc_samples].mean(axis=1)

de = pd.DataFrame({
    'probe_id': expr.index,
    'gene': [probe2gene.get(p, '') for p in expr.index],
    'log2fc': l2fc.values,
    'pvalue': p_vals,
}).dropna()
de['qvalue'] = multipletests(de['pvalue'], method='fdr_bh')[1]

print(f"  Tested: {len(de):,}")
print(f"  q<0.05: {(de['qvalue']<0.05).sum():,}")
print(f"  q<0.05 AND |l2fc|>1: {((de['qvalue']<0.05) & (de['log2fc'].abs()>1)).sum():,}")

# Tumor-UP (variant-specific) genes — UP in SARC relative to UC
sarc_up = de[(de['log2fc'] > 1.0) & (de['qvalue'] < 0.05)].sort_values('log2fc', ascending=False).reset_index(drop=True)

print(f"\nTop 30 genes UP in SARC vs UC (sarcomatoid-specific drug-target candidates):")
print(f"{'Rank':<5}{'Probe':<14}{'Gene':<20}{'log2FC':<10}{'qvalue':<12}")
print('-' * 65)
for i, row in sarc_up.head(30).iterrows():
    g = (str(row.get('gene', '')) or '')[:19]
    print(f"{i+1:<5}{str(row['probe_id'])[:13]:<14}{g:<20}{row['log2fc']:<10.2f}{row['qvalue']:<12.2e}")

# Also DOWN in SARC (lost-in-variant features)
sarc_down = de[(de['log2fc'] < -1.0) & (de['qvalue'] < 0.05)].sort_values('log2fc').reset_index(drop=True)
print(f"\nTop 15 genes DOWN in SARC vs UC (for context):")
for i, row in sarc_down.head(15).iterrows():
    g = (str(row.get('gene', '')) or '')[:19]
    print(f"  {i+1:<3}{g:<20}{row['log2fc']:<10.2f}{row['qvalue']:<12.2e}")

de.to_csv(RESULTS / 'SarcomatoidUC_DE_full.csv', index=False)
sarc_up.to_csv(RESULTS / 'SarcomatoidUC_up.csv', index=False)
sarc_down.to_csv(RESULTS / 'SarcomatoidUC_down.csv', index=False)
print(f"\nSaved → {RESULTS}")
