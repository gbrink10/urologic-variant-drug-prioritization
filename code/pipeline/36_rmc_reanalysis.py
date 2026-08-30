"""Renal medullary carcinoma: what can and cannot be re-analysed, done honestly.

GEO serves no sample-level matrix for GSE180999 - only the authors' own
differential-expression spreadsheet - so the cell-line x treatment x time model
the reviewer asked for cannot be fitted from deposited data. What can be fixed
is the part that was actually wrong in v26-v28:

  * the two patient-derived lines (RMC-2C, RMC219) are treated as two
    independent biological replicates rather than pooled into a single "n=9"
    contrast, and the claim is stated as consistency across the two lines;
  * enrichment uses the genes actually measured in this experiment as the
    background universe, instead of a fixed 20,000;
  * the enrichment is recomputed per cell line and on the intersection, so the
    lead candidate's q-value no longer depends on one line.

Writes: results/refit/RMC_REANALYSIS.csv, results/refit/RMC_ENRICHMENT.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
XL = (REPO / 'data' / 'raw_matrices' / 'GSE180999' /
      'GSE180999_rnaseq_rmc_cell_lines_differential_expression.xlsx')
RF = REPO / 'results' / 'refit'
RF.mkdir(parents=True, exist_ok=True)
SETS = json.loads((REPO / 'results' / 'KEGG_PATHWAYS_18.json')
                  .read_text(encoding='utf-8'))

sheets = pd.read_excel(XL, sheet_name=None)
print("sheets:", list(sheets))

LINES = {'RMC2C': 'RMC2C+SMARCB1', 'RMC219': 'RMC219+SMARCB1'}
frames = {}
for line, sheet in LINES.items():
    df = sheets[sheet].copy()
    df.columns = ['gene', 'l2fc_12h', 'q_12h', 'l2fc_48h', 'q_48h']
    df = df.dropna(subset=['gene'])
    df['gene'] = lib_symbols.normalize(df['gene']).values
    # the deposited contrast is SMARCB1-rescue vs SMARCB1-null; the disease
    # state is SMARCB1-null, so the disease-state orientation is the negative
    for t in ('12h', '48h'):
        df[f'l2fc_disease_{t}'] = -df[f'l2fc_{t}']
    frames[line] = df.drop_duplicates('gene').set_index('gene')
    print(f"  {line}: {len(frames[line]):,} genes")

both = frames['RMC2C'].join(frames['RMC219'], how='inner',
                            lsuffix='_2C', rsuffix='_219')
print(f"  measured in both lines: {len(both):,}")

UP_FC, UP_Q = 0.5, 0.05
for line, suf in (('RMC2C', '_2C'), ('RMC219', '_219')):
    both[f'up_{line}'] = ((both[f'l2fc_disease_48h{suf}'] > UP_FC)
                          & (both[f'q_48h{suf}'] < UP_Q))
both['up_both'] = both['up_RMC2C'] & both['up_RMC219']
both['mean_l2fc_disease_48h'] = both[['l2fc_disease_48h_2C',
                                      'l2fc_disease_48h_219']].mean(axis=1)
both.to_csv(RF / 'RMC_REANALYSIS.csv')

n2c, n219, nboth = (int(both['up_RMC2C'].sum()), int(both['up_RMC219'].sum()),
                    int(both['up_both'].sum()))
print(f"\nup in disease at 48h (log2FC>{UP_FC}, q<{UP_Q}):")
print(f"  RMC-2C only      {n2c:,}")
print(f"  RMC219 only      {n219:,}")
print(f"  consistent both  {nboth:,}")

universe = set(both.index)
rows = []
for label, up in (('RMC-2C', set(both.index[both['up_RMC2C']])),
                  ('RMC219', set(both.index[both['up_RMC219']])),
                  ('both lines', set(both.index[both['up_both']]))):
    recs = []
    for pw, genes in SETS.items():
        gset = set(lib_symbols.normalize(genes)) & universe
        k = len(up & gset)
        p = (1.0 if not gset or not up else
             float(stats.hypergeom.sf(k - 1, len(universe), len(gset), len(up))))
        recs.append({'analysis': label, 'pathway': pw, 'overlap_k': k,
                     'pathway_size_K': len(gset), 'de_set_size_n': len(up),
                     'universe_N': len(universe), 'pvalue': p,
                     'overlap_genes': '; '.join(sorted(up & gset))})
    sub = pd.DataFrame(recs)
    m = len(sub)
    order = np.argsort(sub['pvalue'].values)
    ranked = sub['pvalue'].values[order] * m / (np.arange(m) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(ranked, 1.0)
    sub['qvalue_BH'] = q
    rows.append(sub)

enr = pd.concat(rows, ignore_index=True)
enr.to_csv(RF / 'RMC_ENRICHMENT.csv', index=False)

print("\nenrichment (BH within the eighteen sets, per analysis):")
for label, g in enr.groupby('analysis', sort=False):
    print(f"  {label}")
    for _, r in g.nsmallest(3, 'pvalue').iterrows():
        flag = '  <-- q<0.10' if r['qvalue_BH'] < 0.10 else ''
        print(f"      {r['pathway']:<34} k={r['overlap_k']:<3} "
              f"p={r['pvalue']:.3g}  q={r['qvalue_BH']:.3g}{flag}")

print("\nchemokine-axis genes, per line (disease-state orientation, 48h):")
for g in ['IL8', 'CXCL8', 'CXCL1', 'CXCL2', 'CXCR1', 'CXCR2', 'CEACAM1']:
    if g in both.index:
        r = both.loc[g]
        print(f"  {g:<8} RMC-2C {r['l2fc_disease_48h_2C']:+.2f} "
              f"(q={r['q_48h_2C']:.2g})   RMC219 {r['l2fc_disease_48h_219']:+.2f} "
              f"(q={r['q_48h_219']:.2g})")
    else:
        print(f"  {g:<8} not measured in both lines")
