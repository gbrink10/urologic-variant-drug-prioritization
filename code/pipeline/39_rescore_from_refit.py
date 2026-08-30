"""Recompute every transcriptomic and pathway score component from the refit.

This is the fix for the reproducibility problem: the two data-derived components
are now emitted by one function from the deposited refit tables, so the Master
Table cannot drift from the data it claims to summarise, and every row carries
the numbers behind its own score.

Scoring rules, applied mechanically and identically to all thirty rows:

  transcriptomic (0-3)
    differential-expression arm   3  q < 0.05 and |log2FC| >= 1
                                  2  q < 0.05 and 0.5 <= |log2FC| < 1
                                  1  q < 0.05 and |log2FC| < 0.5
                                  0  not significant after correction
    absolute-expression arm       3  top 5% of measured transcripts
    (used where the dataset has   2  top 15%
     no disease-vs-comparator     1  top 33%
     contrast)                    0  below the top third

  pathway (0-2)
    2  the pathway is enriched at q < 0.10 within its context AND the target is
       a member of that pathway's defining gene set
    1  exactly one of those holds
    0  neither

Writes: results/refit/MASTER_TABLE_V29.csv
        results/refit/SCORING_PROVENANCE_V29.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
PREP = REPO / 'data' / 'prepared'
DE = REPO / 'data' / 'DE_results'

Q_PATHWAY = 0.10          # pre-specified exploratory FDR threshold
defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
# row 27 records its published transcriptomic component as a negative number to
# mark a down-regulated (negative) biomarker; the magnitude is the score
defs['published_E_value'] = (defs['published_E'].astype(str)
                             .str.replace('−', '-', regex=False)
                             .astype(float))
defs['published_E_negative'] = defs['published_E_value'] < 0
SETS = {k: set(lib_symbols.normalize(v)) for k, v in
        json.loads((REPO / 'results' / 'KEGG_PATHWAYS_18.json')
                   .read_text(encoding='utf-8')).items()}

# ---- probe -> symbol maps for the two array platforms ---------------------
sarc = pd.read_csv(DE / 'SarcomatoidUC_DE_full.csv.gz')
SARC_MAP = dict(zip(sarc['probe_id'].astype(str), sarc['gene'].astype(str).str.upper()))
pen = pd.read_csv(DE / 'PenileSCC_DE_full.csv.gz')


def hta_symbol(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    s = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if s in ('---', 'NULL', 'NAN') else s


PSCC_MAP = dict(zip(pen['probe_id'].astype(str), pen['gene'].map(hta_symbol)))
MAPS = {'SarcUC': SARC_MAP, 'PSCC': PSCC_MAP}

_de_cache = {}


def de_table(ctx):
    if ctx in _de_cache:
        return _de_cache[ctx]
    if ctx == 'RMC':
        r = pd.read_csv(RF / 'RMC_REANALYSIS.csv', index_col=0)
        # the two lines are two biological replicates: require consistency and
        # report the mean effect and the weaker of the two q-values
        t = pd.DataFrame({
            'symbol': r.index,
            'logFC': r['mean_l2fc_disease_48h'],
            'adj.P.Val': r[['q_48h_2C', 'q_48h_219']].max(axis=1),
            'consistent': (np.sign(r['l2fc_disease_48h_2C'])
                           == np.sign(r['l2fc_disease_48h_219'])),
        }).reset_index(drop=True)
        t.loc[~t['consistent'], 'adj.P.Val'] = 1.0
    else:
        t = pd.read_csv(RF / f'DE_{ctx}.csv')
        sym = (t['gene'].astype(str).map(MAPS[ctx]) if ctx in MAPS
               else t['gene'].astype(str).str.upper())
        t['symbol'] = lib_symbols.to_symbols(sym.fillna('')).values
        t = t[t['symbol'] != ''].sort_values('P.Value').drop_duplicates('symbol')
    _de_cache[ctx] = t
    return t


_expr_cache = {}


def expr_percentile(ctx, gene):
    """Rank of a gene's mean expression within its own dataset."""
    if ctx not in _expr_cache:
        e = pd.read_csv(PREP / f'{ctx}_expr.csv', index_col=0)
        idx = lib_symbols.to_symbols(e.index).values
        e = e.groupby(idx).max()
        _expr_cache[ctx] = e.mean(axis=1)
    means = _expr_cache[ctx]
    if gene not in means.index:
        return None, len(means)
    pct = float((means < means[gene]).mean() * 100)
    return pct, len(means)


def score_e(row):
    ctx, gene, arm = row['refit_context'], row['scoring_gene'], row['scoring_arm']
    if arm == 'de':
        t = de_table(ctx)
        hit = t[t['symbol'] == gene]
        if not len(hit):
            return None, f'{gene} not measured on the {ctx} platform', np.nan, np.nan
        h = hit.iloc[0]
        fc, q = float(h['logFC']), float(h['adj.P.Val'])
        if q >= 0.05:
            s = 0
        elif abs(fc) >= 1:
            s = 3
        elif abs(fc) >= 0.5:
            s = 2
        else:
            s = 1
        return s, (f'{gene} log2FC {fc:+.2f}, q {q:.3g} ({ctx}, refit)'), fc, q
    pct, n = expr_percentile(ctx, gene)
    if pct is None:
        return None, f'{gene} not measured on the {ctx} platform', np.nan, np.nan
    s = 3 if pct >= 95 else 2 if pct >= 85 else 1 if pct >= 67 else 0
    return s, f'{gene} at {pct:.1f}th percentile of {n:,} measured ({ctx})', np.nan, np.nan


_enr = None


def enrichment(ctx, pathway):
    global _enr
    if _enr is None:
        a = pd.read_csv(RF / 'KEGG_ENRICHMENT_REFIT.csv')
        a = a[a['rule'] == 'q<0.05 & logFC>0.5'][['context', 'pathway', 'qvalue_BH']]
        b = pd.read_csv(RF / 'RMC_ENRICHMENT.csv')
        b = b[b['analysis'] == 'both lines'][['pathway', 'qvalue_BH']]
        b['context'] = 'RMC'
        _enr = pd.concat([a, b[['context', 'pathway', 'qvalue_BH']]],
                         ignore_index=True)
    ctx_map = {'MIBC_KINOME': 'MIBC', 'ccRCC_METS': 'ccRCC'}
    c = ctx_map.get(ctx, ctx)
    hit = _enr[(_enr['context'] == c) & (_enr['pathway'] == pathway)]
    return float(hit['qvalue_BH'].iloc[0]) if len(hit) else None


def score_p(row):
    pw = str(row['pathway_for_component'] or '')
    if not pw:
        return 0, 'row nominated on expression alone; no pathway component', np.nan
    q = enrichment(row['refit_context'], pw)
    member = lib_symbols.normalize([row['scoring_gene']]).iloc[0] in SETS.get(pw, set())
    enriched = q is not None and q < Q_PATHWAY
    s = 2 if (enriched and member) else 1 if (enriched or member) else 0
    basis = (f'{pw}: q {"n/a" if q is None else f"{q:.3g}"} '
             f'({"enriched" if enriched else "not enriched"} at q<{Q_PATHWAY}); '
             f'target {"in" if member else "not in"} pathway set')
    return s, basis, (np.nan if q is None else q)


out, prov = [], []
for _, r in defs.iterrows():
    e, e_basis, fc, q = score_e(r)
    # a target absent from its dataset's platform cannot be scored from data;
    # the row keeps its curated value and is flagged as not re-derivable
    derivable = e is not None
    if not derivable:
        e = int(abs(r['published_E_value']))
        e_basis += '; NOT RE-DERIVABLE - curated value retained'
    p, p_basis, pq = score_p(r)
    g, l = int(r['genomic_score_curated']), int(r['literature_score_curated'])
    total = g + e + p + l
    tier = ('Strong' if total >= 7 else 'Moderate' if total >= 4
            else 'Exploratory' if total >= 1 else 'None')
    out.append({'N': r['N'], 'Context': r['Context'], 'Drug': r['Drug'],
                'Target': r['Target'], 'G(0-3)': g, 'E(0-3)': e, 'P(0-2)': p,
                'L(0-1)': l, 'Total': f'{total}/9', 'Tier': tier,
                'Stage': r['Stage'], 'Prior status': r['Prior status'],
                'Trial readiness': r['Trial readiness']})
    prov.append({'N': r['N'], 'Context': r['Context'], 'Target': r['Target'],
                 'scoring_gene': r['scoring_gene'], 'arm': r['scoring_arm'],
                 'refit_context': r['refit_context'],
                 'E_refit': e, 'E_published': r['published_E'],
                 'E_derivable_from_data': derivable,
                 'E_basis': e_basis, 'refit_log2FC': fc, 'refit_q': q,
                 'P_refit': p, 'P_published': r['published_P'],
                 'P_basis': p_basis, 'pathway_q': pq,
                 'G_curated': g, 'L_curated': l, 'Total': total, 'Tier': tier})

mt = pd.DataFrame(out)
pv = pd.DataFrame(prov)
mt.to_csv(RF / 'MASTER_TABLE_V29.csv', index=False)
pv.to_csv(RF / 'SCORING_PROVENANCE_V29.csv', index=False)

print("RESCORED MASTER TABLE\n")
print(f"{'N':<3}{'Context':<17}{'Target':<30}{'G':>2}{'E':>2}{'P':>2}{'L':>2}"
      f"{'Tot':>5}  {'Tier':<12}{'E was':>6}{'P was':>6}")
for (_, m), (_, p) in zip(mt.iterrows(), pv.iterrows()):
    chg = '' if (p['E_refit'] == p['E_published'] and p['P_refit'] == p['P_published']) \
        else '   <-- changed'
    print(f"{m['N']:<3}{m['Context']:<17}{str(m['Target'])[:28]:<30}"
          f"{m['G(0-3)']:>2}{m['E(0-3)']:>2}{m['P(0-2)']:>2}{m['L(0-1)']:>2}"
          f"{m['Total']:>5}  {m['Tier']:<12}{p['E_published']:>6}"
          f"{p['P_published']:>6}{chg}")

print("\ntier distribution:", mt['Tier'].value_counts().to_dict())
pub_e = (pv['E_published'].astype(str).str.replace('−', '-', regex=False)
         .astype(float).abs())
changed = pv[(pv['E_refit'] != pub_e) | (pv['P_refit'] != pv['P_published'])]
print(f"rows whose data-derived components changed: {len(changed)} of {len(pv)}")
print(f"\nwrote {RF / 'MASTER_TABLE_V29.csv'}")
