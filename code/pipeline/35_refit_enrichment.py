"""Recompute pathway enrichment from the design-aware refit.

Three things change relative to the v26-v28 enrichment:

  * the input gene lists come from limma/edgeR fits rather than per-gene t-tests;
  * the background universe is the set of genes actually measured and retained in
    that dataset, not a fixed 20,000 (which inflated every hypergeometric test on
    a targeted panel);
  * both a q-based and a p-based gene list are run, so the manuscript can report
    how much the enrichment depends on the significance rule.

Writes: results/refit/KEGG_ENRICHMENT_REFIT.csv
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
RF = REPO / 'results' / 'refit'
DE = REPO / 'data' / 'DE_results'

SETS = json.loads((REPO / 'results' / 'KEGG_PATHWAYS_18.json')
                  .read_text(encoding='utf-8'))

# probe -> symbol for the two array platforms
sarc = pd.read_csv(DE / 'SarcomatoidUC_DE_full.csv.gz')
SARC_MAP = dict(zip(sarc['probe_id'].astype(str), sarc['gene'].astype(str).str.upper()))
pen = pd.read_csv(DE / 'PenileSCC_DE_full.csv.gz')


def hta_symbol(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    sym = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if sym in ('---', 'NULL', 'NAN') else sym


PSCC_MAP = dict(zip(pen['probe_id'].astype(str), pen['gene'].map(hta_symbol)))
MAPS = {'SarcUC': SARC_MAP, 'PSCC': PSCC_MAP}

# refit context -> the context label the manuscript uses
CONTEXTS = {
    'PSCC': 'PSCC', 'SarcUC': 'SarcUC', 'SCBC_ASCL1': 'SCBC_ASCL1',
    'SCBC_NEUROD1': 'SCBC_NEUROD1', 'SCBC_POU2F3': 'SCBC_POU2F3',
    'SCBC_YAP1': 'SCBC_YAP1', 'NEPC_CXCR7': 'NEPC_CXCR7',
    'NEPC_DECITABINE': 'NEPC_DECITABINE', 'NEPC_DNMT': 'NEPC_DNMT',
    'MIBC_KINOME': 'MIBC', 'ccRCC_METS': 'ccRCC', 'HLRCC': 'HLRCC',
}


def symbols(ctx, df):
    if ctx in MAPS:
        s = df['gene'].astype(str).map(MAPS[ctx])
    else:
        s = df['gene'].astype(str).str.upper()
    s = s.fillna('')
    return pd.Series(lib_symbols.normalize(s).values, index=df.index)


rows = []
for ctx, label in CONTEXTS.items():
    f = RF / f'DE_{ctx}.csv'
    if not f.exists():
        print(f"  skip {ctx}: no refit table")
        continue
    df = pd.read_csv(f)
    df['symbol'] = symbols(ctx, df)
    df = df[df['symbol'] != '']
    # collapse probes to genes on the most significant probe
    df = df.sort_values('P.Value').drop_duplicates('symbol')
    universe = set(df['symbol'])

    for rule, mask in (
            ('q<0.05 & logFC>0.5', (df['adj.P.Val'] < 0.05) & (df['logFC'] > 0.5)),
            ('p<0.05 & logFC>0.5', (df['P.Value'] < 0.05) & (df['logFC'] > 0.5))):
        up = set(df.loc[mask, 'symbol'])
        recs = []
        for pw, genes in SETS.items():
            gset = set(lib_symbols.normalize(genes)) & universe
            k = len(up & gset)
            K, n, N = len(gset), len(up), len(universe)
            if K == 0 or n == 0:
                p = 1.0
            else:
                p = float(stats.hypergeom.sf(k - 1, N, K, n))
            recs.append({'context': label, 'refit_context': ctx, 'rule': rule,
                         'pathway': pw, 'overlap_k': k, 'pathway_size_K': K,
                         'de_set_size_n': n, 'universe_N': N, 'pvalue': p,
                         'overlap_genes': '; '.join(sorted(up & gset))})
        sub = pd.DataFrame(recs)
        # Benjamini-Hochberg within this context and rule, across the 18 sets
        order = np.argsort(sub['pvalue'].values)
        m = len(sub)
        q = np.empty(m)
        ranked = sub['pvalue'].values[order] * m / (np.arange(m) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        q[order] = np.minimum(ranked, 1.0)
        sub['qvalue_BH'] = q
        rows.append(sub)

out = pd.concat(rows, ignore_index=True)
out.to_csv(RF / 'KEGG_ENRICHMENT_REFIT.csv', index=False)

print("ENRICHMENT AFTER REFIT (primary rule: q<0.05 & logFC>0.5)\n")
prim = out[out['rule'] == 'q<0.05 & logFC>0.5']
for label, g in prim.groupby('context', sort=False):
    best = g.nsmallest(3, 'pvalue')
    n = int(g['de_set_size_n'].iloc[0])
    N = int(g['universe_N'].iloc[0])
    print(f"  {label:<16} up={n:<6} universe={N:<6}")
    for _, r in best.iterrows():
        star = '  <-- q<0.10' if r['qvalue_BH'] < 0.10 else ''
        print(f"      {r['pathway']:<34} k={r['overlap_k']:<3} "
              f"p={r['pvalue']:.3g}  q={r['qvalue_BH']:.3g}{star}")
print(f"\nwrote {RF / 'KEGG_ENRICHMENT_REFIT.csv'}")
