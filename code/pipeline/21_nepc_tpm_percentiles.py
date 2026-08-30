"""Resolve the neuroendocrine prostate cancer expression values from the primary
GEO matrices, and place each in its dataset's expression distribution.

Four Master Table 1 rows (venetoclax/BCL2, tazemetostat/EZH2, decitabine/DNMT1,
olaparib/PARP1-2) were scored on absolute expression rather than fold change. The
values recorded in the v25 validation table could not all be reconciled against
the derived DE tables, so this script goes back to the author-deposited GEO
expression matrices:

  GSE216053_TPM_PM154_decitabine.txt.gz   TPM, PM154, control vs decitabine D14
  GSE216052_TPM_PM154_sgDNMTs.txt.gz      TPM, PM154, WT vs DNMT1/DNMT3A knockout
  GSE199274_mr99-mr110_RPKM.txt.gz        RPKM, MDVr series

DNMT1 acts as the internal control: the v25 table records TPM = 123.6, so
recovering that value from the primary matrix confirms both the Ensembl mapping
and the provenance of the quoted numbers.

Writes: results/NEPC_TPM_PERCENTILES.csv
"""
import gzip
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
DATA = Path(r"C:\Users\garre\framework_expansion\data")
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results' / 'NEPC_TPM_PERCENTILES.csv'

# stable Ensembl gene IDs for the transcripts scored in rows 1, 3, 4 and 6
GENES = {
    'BCL2':  'ENSG00000171791',
    'EZH2':  'ENSG00000106462',
    'DNMT1': 'ENSG00000130816',
    'PARP1': 'ENSG00000143799',
    'PARP2': 'ENSG00000129484',
    'RB1':   'ENSG00000139687',
    'AURKA': 'ENSG00000087586',
}
QUOTED = {'BCL2': 34.3, 'EZH2': 39.7, 'DNMT1': 123.6,
          'PARP1': 267.0, 'PARP2': 45.0, 'RB1': 2.7}

rows = []


def percentile(series: pd.Series, value: float) -> float:
    return float((series < value).mean() * 100)


# ---------------- GSE216053 (TPM, gene level) ----------------
with gzip.open(DATA / 'GSE216053_TPM_PM154_decitabine.txt.gz', 'rt') as f:
    g53 = pd.read_csv(f, sep='\t', index_col=0)
ctrl53 = g53[[c for c in g53.columns if c.startswith('control')]].mean(axis=1)
print(f"GSE216053: {g53.shape[0]} genes x {g53.shape[1]} samples "
      f"(control mean over {len([c for c in g53.columns if c.startswith('control')])})")

# ---------------- GSE216052 (TPM, transcript level -> gene) ----------------
with gzip.open(DATA / 'GSE216052_TPM_PM154_sgDNMTs.txt.gz', 'rt') as f:
    g52 = pd.read_csv(f, sep='\t')
wt_cols = [c for c in g52.columns if c.startswith('WT_')]
g52_gene = g52.groupby('ensgene')[wt_cols].sum().mean(axis=1)
print(f"GSE216052: {g52.shape[0]} transcripts -> {g52_gene.shape[0]} genes "
      f"(WT mean over {len(wt_cols)})")

# ---------------- GSE199274 (RPKM, symbol level) ----------------
with gzip.open(DATA / 'GSE199274_mr99-mr110_RPKM.txt.gz', 'rt') as f:
    g99 = pd.read_csv(f, sep='\t', index_col=0)
g99_mean = g99.mean(axis=1)
print(f"GSE199274: {g99.shape[0]} genes x {g99.shape[1]} samples\n")

SOURCES = [
    ('GSE216053 (TPM, PM154 control)', ctrl53, 'ensembl'),
    ('GSE216052 (TPM, PM154 WT)', g52_gene, 'ensembl'),
    ('GSE199274 (RPKM, MDVr mean)', g99_mean, 'symbol'),
]

for gene, ensg in GENES.items():
    for label, series, key in SOURCES:
        idx = ensg if key == 'ensembl' else gene
        if idx not in series.index:
            continue
        val = float(series.loc[idx])
        expressed = series[series > 0]
        pct_all = percentile(series, val)
        pct_expr = percentile(expressed, val)
        rows.append({
            'gene': gene, 'source': label,
            'value': round(val, 3),
            'v25_quoted': QUOTED.get(gene),
            'pct_all_genes': round(pct_all, 2),
            'pct_expressed_genes': round(pct_expr, 2),
            'top_1pct_of_expressed': pct_expr >= 99.0,
        })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
print(df.to_string(index=False))

print("\n--- internal control ---")
d = df[(df['gene'] == 'DNMT1') & (df['source'].str.startswith('GSE216053'))]
if not d.empty:
    v = float(d['value'].iloc[0])
    print(f"DNMT1 in GSE216053 control = {v:.2f}; v25 recorded 123.6 -> "
          f"{'CONFIRMS the quoted provenance' if abs(v - 123.6) < 5 else 'DOES NOT match'}")

print("\n--- do the quoted values now reconcile? ---")
for gene, q in QUOTED.items():
    sub = df[df['gene'] == gene]
    if sub.empty:
        print(f"  {gene:<6} quoted {q}: gene not found in any matrix")
        continue
    best = sub.iloc[(sub['value'] - q).abs().argsort().iloc[0]]
    ok = abs(best['value'] - q) <= max(1.0, 0.1 * q)
    print(f"  {gene:<6} quoted {q:<7} closest {best['value']:<9} "
          f"({best['source']}) -> {'reconciles' if ok else 'still unreconciled'}")

print(f"\nWrote {OUT}")
