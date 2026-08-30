"""Audit the GEO transcriptomic (E) component of the Molecular Prioritization Score.

The E component is defined in the manuscript as explicit bins over the
per-context differential-expression result:

    3  significant DE with |log2FC| >= 1, or within the top 1% of transcripts
    2  significant DE with 0.5 <= |log2FC| < 1
    1  significant DE with |log2FC| < 0.5
    0  otherwise

This script recomputes that component directly from the deposited DE tables
for every Master Table 1 row whose nominated target maps to a measured
transcript, and reports any row where the recomputed value differs from the
value carried in MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv. It exists so the
score is machine-checkable from the deposited data rather than taken on trust.

Writes: results/GEO_SCORE_AUDIT.csv
"""
import sys
from pathlib import Path
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
DE = REPO / 'data' / 'DE_results'
RESULTS = REPO / 'results'

# Master Table 1 row -> (context label in DE table, transcript actually driving
# the row).  Where a row is driven by a ligand/partner rather than the drug
# target itself, the transcript scored is named here explicitly.
ROW_TRANSCRIPT = {
    17: ('RMC',                    'IL8',      'CXCR1/CXCR2 - scored on IL8/CXCL8 ligand'),
    18: ('RMC',                    'HBEGF',    'EGFR - scored on HBEGF ligand'),
    19: ('RMC',                    'CEACAM1',  'CM24 - target transcript'),
    20: ('Penile SCC',             'HLA-DRA',  'PD-1 - scored on immune-hot marker HLA-DRA'),
    21: ('Penile SCC',             'MMP1',     'MMP inhibitor - target transcript'),
    22: ('Penile SCC',             'POSTN',    'TGFB axis - scored on POSTN'),
    23: ('Sarcomatoid UC',         'WHSC1',    'NSD2/WHSC1 - target transcript'),
    24: ('Sarcomatoid UC',         'ATRIP',    'ATR - scored on ATRIP'),
    25: ('Sarcomatoid UC',         'UHRF1',    'UHRF1 - target transcript'),
    26: ('Sarcomatoid UC',         'G6PD',     'G6PD - target transcript'),
    28: ('SCBC ASCL1+ subtype',    'CEACAM5',  'CEACAM5 - target transcript'),
    29: ('SCBC NEUROD1+ subtype',  'SSTR2',    'SSTR2 - target transcript'),
    30: ('SCBC POU2F3+ subtype',   'PTGS1',    'COX-1/PTGS1 - target transcript'),
}

# RMC is deposited as rescue-vs-null, so the disease-state log2FC is negated.
DISEASE_ORIENTATION_FLIP = {'RMC'}


def e_component(abs_l2fc: float, significant: bool) -> int:
    if not significant:
        return 0
    if abs_l2fc >= 1.0:
        return 3
    if abs_l2fc >= 0.5:
        return 2
    return 1


de = pd.read_csv(DE / 'FULL_DE_RESULTS_ALL10.csv')
master = pd.read_csv(RESULTS / 'MASTER_DRUG_ASSOCIATION_TABLE_30_ROWS.csv')
master['N'] = pd.to_numeric(master['N'], errors='coerce')

rows = []
for n, (ctx, gene, note) in sorted(ROW_TRANSCRIPT.items()):
    sub = de[(de['context'] == ctx) & (de['gene_symbol'].astype(str).str.upper() == gene.upper())]
    if sub.empty:
        rows.append({'row': n, 'context': ctx, 'transcript': gene,
                     'log2FC_disease': None, 'q': None,
                     'E_recomputed': None, 'E_in_table': None,
                     'agrees': 'TRANSCRIPT NOT IN DEPOSITED DE TABLE',
                     'note': note})
        continue
    r = sub.iloc[0]
    l2fc = float(r['log2FC_disease_state'])
    if ctx in DISEASE_ORIENTATION_FLIP:
        q = min(float(r['qval_48h_RMC2C']), float(r['qval_48h_RMC219']))
    else:
        q = float(r['qvalue'])
    e_new = e_component(abs(l2fc), q < 0.05)
    mrow = master[master['N'] == n]
    e_old = int(mrow['GEO(0-3)'].iloc[0]) if not mrow.empty else None
    rows.append({'row': n, 'context': ctx, 'transcript': gene,
                 'log2FC_disease': round(l2fc, 3), 'q': f'{q:.3g}',
                 'E_recomputed': e_new, 'E_in_table': e_old,
                 'agrees': 'yes' if e_new == e_old else 'NO - REVIEW',
                 'note': note})

out = pd.DataFrame(rows)
out.to_csv(RESULTS / 'GEO_SCORE_AUDIT.csv', index=False)

print(out.to_string(index=False))
mismatch = out[out['agrees'] == 'NO - REVIEW']
print(f"\n{len(mismatch)} of {len(out)} auditable rows disagree with the table as built.")
if len(mismatch):
    for _, r in mismatch.iterrows():
        print(f"  row {int(r['row'])}: {r['transcript']} log2FC={r['log2FC_disease']} "
              f"q={r['q']} -> E should be {r['E_recomputed']}, table has {r['E_in_table']}")
print(f"\nWrote {RESULTS / 'GEO_SCORE_AUDIT.csv'}")
