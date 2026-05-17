"""Translocation RCC DE analysis from GSE150474.

51 total samples; key cleanest comparison:
  - 12 Xp11 renal cell carcinoma vs 7 normal kidney controls

Platform-specific: NanoString-style with VALUE per probe (or microarray on
Illumina/Affymetrix). Need to inspect.
"""
import sys, os, re
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
print("Translocation RCC DE: GSE150474 (12 Xp11 RCC vs 7 Normal kidney)")
print("=" * 70)

gse = GEOparse.get_GEO(geo='GSE150474', destdir='.', silent=True)
print(f"Platform: {gse.metadata.get('platform_id', [''])[0]}")

# Group samples
sample_groups = {}
for gsm_id, gsm in gse.gsms.items():
    title = gsm.metadata.get('title', [''])[0]
    if title.startswith('Xp11 renal cell carcinoma'):
        sample_groups[gsm_id] = 'xp11_rcc'
    elif title.startswith('Normal tissue'):
        # Check tissue:kidney
        chars = gsm.metadata.get('characteristics_ch1', [])
        is_kidney = any('tissue: kidney' in c.lower() for c in chars)
        if is_kidney:
            sample_groups[gsm_id] = 'normal_kidney'

print(f"  Xp11 RCC: {sum(1 for v in sample_groups.values() if v == 'xp11_rcc')}")
print(f"  Normal kidney: {sum(1 for v in sample_groups.values() if v == 'normal_kidney')}")

# Build expression matrix
first_gsm = list(gse.gsms.values())[0]
print(f"\nFirst sample table: {len(first_gsm.table)} rows, cols={list(first_gsm.table.columns)}")
print(first_gsm.table.head(3).to_string(index=False))

expr_data = {}
for gsm_id in sample_groups:
    gsm = gse.gsms[gsm_id]
    tbl = gsm.table
    expr_data[gsm_id] = pd.Series(tbl['VALUE'].values, index=tbl['ID_REF'].values)
expr = pd.DataFrame(expr_data).apply(pd.to_numeric, errors='coerce').dropna()
print(f"\nExpression matrix: {expr.shape}")

# Get platform annotation for symbol
print(f"\nFetching platform annotation...")
plat_id = gse.metadata.get('platform_id', [''])[0]
gpl = GEOparse.get_GEO(geo=plat_id, destdir='.', silent=True)
ann = gpl.table
print(f"  Annotation cols: {list(ann.columns)[:12]}")

# Find symbol column
sym_col = None
for c in ann.columns:
    if c.lower() in ('symbol', 'gene symbol', 'genesymbol', 'gene_symbol'):
        sym_col = c; break
if sym_col is None:
    for c in ann.columns:
        if 'symbol' in c.lower() or 'gene' in c.lower():
            sym_col = c; break
id_col = ann.columns[0]
print(f"  Using {id_col}=probe, {sym_col}=gene")
probe2gene = ann.set_index(id_col)[sym_col].to_dict() if sym_col else {}

# DE: tumor vs normal
tumor = [s for s, g in sample_groups.items() if g == 'xp11_rcc']
normal = [s for s, g in sample_groups.items() if g == 'normal_kidney']
print(f"\nDE: Xp11 RCC (n={len(tumor)}) vs Normal kidney (n={len(normal)})")

stat_vals, p_vals = stats.ttest_ind(expr[tumor].values, expr[normal].values, axis=1, equal_var=False)
l2fc = expr[tumor].mean(axis=1) - expr[normal].mean(axis=1)
de = pd.DataFrame({
    'probe_id': expr.index,
    'gene': [probe2gene.get(p, '') for p in expr.index],
    'log2fc': l2fc.values,
    'pvalue': p_vals,
}).dropna()
de['qvalue'] = multipletests(de['pvalue'], method='fdr_bh')[1]

print(f"  Probes: {len(de):,}; q<0.05: {(de['qvalue']<0.05).sum():,}")
print(f"  q<0.05 AND log2FC>1: {((de['qvalue']<0.05) & (de['log2fc']>1)).sum():,}")

# Aggregate by gene symbol — take max abs log2FC per gene
de_gene = de[de['gene'].notna() & (de['gene'] != '')].copy()
de_gene = de_gene.assign(abs_l2fc=de_gene['log2fc'].abs())
de_gene = de_gene.sort_values('abs_l2fc', ascending=False).drop_duplicates('gene')

tumor_up = de_gene[(de_gene['log2fc'] > 1.0) & (de_gene['qvalue'] < 0.05)].sort_values('log2fc', ascending=False).reset_index(drop=True)
print(f"\nTop 30 genes UP in Xp11 RCC (per-gene; unique):")
print(f"{'Rank':<5}{'Gene':<20}{'log2FC':<10}{'qvalue':<12}")
print('-' * 50)
for i, row in tumor_up.head(30).iterrows():
    g = str(row.get('gene', ''))[:19]
    print(f"{i+1:<5}{g:<20}{row['log2fc']:<10.2f}{row['qvalue']:<12.2e}")

de.to_csv(RESULTS / 'TranslocationRCC_DE_full.csv', index=False)
tumor_up.to_csv(RESULTS / 'TranslocationRCC_up.csv', index=False)
print(f"\nSaved → {RESULTS}")
