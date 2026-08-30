"""Test the expression-rank arm of the E rule for the rows scored on it.

The E component awards 3 points for "significant differential expression with
|log2FC| >= 1, OR expression within the top 1% of expressed transcripts". Four
source-disease rows were scored from absolute expression levels (TPM) rather
than fold change, per the v25 validation table. This script places each quoted
value in the distribution of its own dataset and reports whether the top-1% arm
is actually met, and whether the quoted value can be reconciled with the
deposited expression means at all.

Writes: results/EXPRESSION_RANK_AUDIT.csv
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
LEGACY = REPO / 'legacy' / 'v25' / 'data' / 'FULL_DE_RESULTS_with_qvalues.csv'
OUT = REPO / 'results' / 'EXPRESSION_RANK_AUDIT.csv'

# (row, gene, value quoted in the v25 validation table, dataset it is attributed to)
QUOTED = [
    (1, 'BCL2',   34.3,  'GSE216053'),
    (3, 'EZH2',   39.7,  'GSE216053'),
    (4, 'DNMT1',  123.6, 'GSE216053'),
    (6, 'PARP1',  267.0, 'GSE216053'),
    (6, 'PARP2',  45.0,  'GSE216053'),
    (14, 'VEGFA', None,  'GSE143630'),   # recorded as rank 30/57,353
    (15, 'EPAS1', None,  'GSE143630'),   # recorded as rank 75/57,353
    (16, 'CDK4',  None,  'GSE143630'),   # recorded as top 8.2%
]

de = pd.read_csv(LEGACY)
de['gene_u'] = de['gene'].astype(str).str.upper()

rows = []
for row, gene, quoted, dataset in QUOTED:
    sub = de[de['dataset'] == dataset]
    hit = sub[sub['gene_u'] == gene]

    rec = {'row': row, 'gene': gene, 'quoted_value': quoted,
           'attributed_dataset': dataset}

    if hit.empty:
        # where else does this gene appear?
        elsewhere = de[de['gene_u'] == gene]
        alt = ''
        if not elsewhere.empty:
            a = elsewhere.sort_values('mean_a', ascending=False).iloc[0]
            asub = de[de['dataset'] == a['dataset']]
            apct = float((asub['mean_a'] < a['mean_a']).mean() * 100)
            alt = (f"highest elsewhere: {a['dataset']} mean={a['mean_a']:.2f} "
                   f"({apct:.2f}th pct)")
        rec.update({'deposited_mean': None, 'percentile': None,
                    'top_1pct_met': False,
                    'verdict': f'ABSENT from attributed dataset; {alt}'})
        rows.append(rec)
        continue

    v = float(hit.iloc[0]['mean_a'])
    pct = float((sub['mean_a'] < v).mean() * 100)
    met = pct >= 99.0
    if quoted is None:
        match = 'n/a (rank recorded, not a value)'
    elif abs(v - quoted) < 1.0:
        match = 'reconciles with quoted value'
    else:
        match = f'DOES NOT reconcile (deposited mean {v:.2f} vs quoted {quoted})'
    rec.update({'deposited_mean': round(v, 3), 'percentile': round(pct, 2),
                'top_1pct_met': met,
                'verdict': f"{'top 1% MET' if met else f'top 1% NOT met (top {100 - pct:.1f}%)'}; {match}"})
    rows.append(rec)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print(out.to_string(index=False))
print(f"\nrows scored on the expression-rank arm that actually meet it: "
      f"{int(out['top_1pct_met'].sum())} of {len(out)}")
print(f"\nWrote {OUT}")
