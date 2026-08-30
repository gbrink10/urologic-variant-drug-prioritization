"""Extend the GEO-component audit to Master Table 1 rows 1-16.

14_audit_geo_score_component.py covers the rare-disease rows, whose DE tables are
deposited in data/DE_results/. Rows 1-16 draw on the source-disease datasets,
whose DE tables live in legacy/v25/.

Two things this script is careful about:

1. Each row is checked ONLY against the dataset(s) the manuscript attributes it
   to. Searching across all datasets pulls nonsense matches (a DNMT value from a
   clear cell renal cohort says nothing about a neuroendocrine prostate row).

2. The E rule has two arms: significant DE with |log2FC| >= 1, OR expression
   within the top 1% of transcripts. Several source-disease rows were scored on
   the second arm (the row-1 build comment records "BCL2 TPM=34.3"), so testing
   only fold change would wrongly mark them unsupported. Both arms are evaluated
   and reported separately.

Writes: results/SOURCE_DISEASE_SCORE_AUDIT.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
LEGACY = REPO / 'legacy' / 'v25' / 'data' / 'FULL_DE_RESULTS_with_qvalues.csv'
MASTER = REPO / 'results' / 'MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv'
OUT = REPO / 'results' / 'SOURCE_DISEASE_SCORE_AUDIT.csv'

# row -> (datasets that legitimately speak to this row, transcript(s) scored)
ROWS = {
    1:  (['GSE199274', 'GSE216053'], ['BCL2']),
    2:  (['GSE199274', 'GSE216053'], ['AURKA']),
    3:  (['GSE199274', 'GSE216053'], ['EZH2']),
    4:  (['GSE216052'],              ['DNMT1', 'DNMT3A', 'DNMT3B']),
    5:  ([],                         ['TP53']),          # genomic-only row, E=0
    6:  (['GSE199274', 'GSE216053'], ['PARP1', 'PARP2']),
    7:  (['GSE130598'],              ['AURKA', 'AURKB']),
    8:  (['GSE130598'],              ['ATR']),   # per v25 validation table
    9:  (['GSE130598'],              ['PIK3CA']),
    10: (['GSE130598'],              ['FGFR2', 'FGFR3']),
    11: (['GSE130598'],              ['NECTIN4', 'PVRL4']),
    12: (['GSE130598'],              ['PDCD1', 'CD274']),
    13: (['GSE130598'],              ['CDK4', 'CDK6', 'CDKN2A']),
    14: (['GSE143630'],              ['KDR', 'FLT1', 'VEGFA']),
    15: (['GSE143630'],              ['EPAS1']),
    16: (['GSE143630'],              ['CDK4', 'CDK6']),
}

de = pd.read_csv(LEGACY)
de['gene_u'] = de['gene'].astype(str).str.upper()
de['peak_mean'] = de[['mean_a', 'mean_b']].max(axis=1)

# expression percentile within each dataset (for the top-1% arm)
de['expr_pct'] = de.groupby('dataset')['peak_mean'].rank(pct=True) * 100

master = pd.read_csv(MASTER)
master['N_num'] = pd.to_numeric(master['N'], errors='coerce')

rows = []
for n, (datasets, genes) in sorted(ROWS.items()):
    mrow = master[master['N_num'] == n]
    e_table = int(mrow['GEO(0-3)'].iloc[0]) if not mrow.empty else None
    drug = mrow['Drug'].iloc[0] if not mrow.empty else ''

    rec = {'row': n, 'drug': drug[:34], 'datasets': '/'.join(datasets) or 'none',
           'genes': '/'.join(genes), 'E_in_table': e_table}

    if not datasets:
        rec.update({'verdict': 'n/a - genomic-only row', 'E_recomputed': e_table})
        rows.append(rec)
        continue

    hits = de[(de['dataset'].isin(datasets)) &
              (de['gene_u'].isin([g.upper() for g in genes]))]
    if hits.empty:
        rec.update({'log2FC': None, 'q': None, 'expr_pct': None,
                    'E_recomputed': None,
                    'verdict': 'NO DEPOSITED DATA for the cited dataset'})
        rows.append(rec)
        continue

    best_fc = hits.loc[hits['log2FC'].abs().idxmax()]
    best_expr = hits.loc[hits['expr_pct'].idxmax()]

    fc_arm = (abs(float(best_fc['log2FC'])) >= 1) and (float(best_fc['q_value']) < 0.05)
    top1_arm = float(best_expr['expr_pct']) >= 99.0

    if fc_arm or top1_arm:
        e_new = 3
    elif float(best_fc['q_value']) < 0.05 and abs(float(best_fc['log2FC'])) >= 0.5:
        e_new = 2
    elif float(best_fc['q_value']) < 0.05:
        e_new = 1
    else:
        e_new = 0

    rec.update({'log2FC': round(float(best_fc['log2FC']), 3),
                'q': f"{float(best_fc['q_value']):.3g}",
                'expr_pct': round(float(best_expr['expr_pct']), 2),
                'E_recomputed': e_new,
                'verdict': 'agrees' if e_new == e_table else 'DISAGREES'})
    rows.append(rec)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
cols = ['row', 'datasets', 'genes', 'log2FC', 'q', 'expr_pct',
        'E_recomputed', 'E_in_table', 'verdict']
print(out[[c for c in cols if c in out.columns]].to_string(index=False))

nodata = out[out['verdict'].astype(str).str.startswith('NO DEPOSITED')]
disagree = out[out['verdict'] == 'DISAGREES']
agree = out[out['verdict'].isin(['agrees', 'n/a - genomic-only row'])]
print(f"\nreconcile: {len(agree)}   disagree: {len(disagree)}   "
      f"no deposited data: {len(nodata)}   (of {len(out)})")
if len(nodata):
    print("rows with no deposited data:", list(nodata['row']))
print(f"\nWrote {OUT}")
