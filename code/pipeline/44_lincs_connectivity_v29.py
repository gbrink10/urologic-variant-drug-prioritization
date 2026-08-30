"""Re-run the LINCS connectivity analysis on the refit gene lists.

Unlike the protein, dependency and compound layers - which are per-gene or
per-compound lookups and are unaffected by refitting the differential expression
- connectivity is computed FROM the up-regulated gene lists. Refitting the DE
therefore invalidates the previous result, and this recomputes it.

Method unchanged from 28_lincs_connectivity.py: for each context the
significantly up-regulated genes are tested against the LINCS L1000
chemical-perturbation libraries through the Enrichr API. Enrichment in the
down-perturbation library means a compound reverses the disease signature (the
therapeutic direction); enrichment in the up-perturbation library means it
reproduces the signature and is reported as an internal control.

Writes: results/refit/LINCS_CONNECTIVITY_V29.csv
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
DEDIR = REPO / 'data' / 'DE_results'
OUT = RF / 'LINCS_CONNECTIVITY_V29.csv'
BASE = "https://maayanlab.cloud/Enrichr"

LIBS = {'reversal': 'LINCS_L1000_Chem_Pert_down',
        'mimicry (control)': 'LINCS_L1000_Chem_Pert_up'}

NOMINATED = ['reparixin', 'navarixin', 'azd5069', 'danirixin', 'ladarixin',
             'erlotinib', 'ceralasertib', 'berzosertib', 'celecoxib', 'aspirin',
             'venetoclax', 'alisertib', 'tazemetostat', 'decitabine',
             'azacitidine', 'olaparib', 'talazoparib', 'alpelisib', 'erdafitinib',
             'palbociclib', 'abemaciclib', 'pazopanib', 'marimastat', 'polydatin',
             'bortezomib']

# probe -> symbol for the two array platforms
sarc = pd.read_csv(DEDIR / 'SarcomatoidUC_DE_full.csv.gz')
SARC_MAP = dict(zip(sarc['probe_id'].astype(str), sarc['gene'].astype(str).str.upper()))
pen = pd.read_csv(DEDIR / 'PenileSCC_DE_full.csv.gz')


def hta_symbol(ann):
    parts = str(ann).split(' /// ')[0].split(' // ')
    s = parts[1].strip().upper() if len(parts) > 1 else ''
    return '' if s in ('---', 'NULL', 'NAN') else s


PSCC_MAP = dict(zip(pen['probe_id'].astype(str), pen['gene'].map(hta_symbol)))
MAPS = {'SarcUC': SARC_MAP, 'PSCC': PSCC_MAP}

CONTEXTS = {
    'PSCC': 'penile squamous cell carcinoma',
    'SarcUC': 'sarcomatoid urothelial carcinoma',
    'SCBC_ASCL1': 'SCBC ASCL1+', 'SCBC_NEUROD1': 'SCBC NEUROD1+',
    'SCBC_POU2F3': 'SCBC POU2F3+', 'HLRCC': 'HLRCC',
    'MIBC_KINOME': 'muscle-invasive bladder cancer',
}


def post_genes(genes, description):
    boundary = '----EnrichrBoundary'
    parts = []
    for key, val in [('list', '\n'.join(genes)), ('description', description)]:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"'
                     f'\r\n\r\n{val}\r\n')
    body = (''.join(parts) + f'--{boundary}--\r\n').encode()
    req = urllib.request.Request(
        f'{BASE}/addList', data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())['userListId']


def enrich(list_id, library):
    url = f'{BASE}/enrich?userListId={list_id}&backgroundType={library}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())[library]


def up_genes(ctx):
    """Up-regulated genes for a context, from the refit."""
    if ctx == 'RMC':
        r = pd.read_csv(RF / 'RMC_REANALYSIS.csv', index_col=0)
        return sorted(set(r.index[r['up_both'].fillna(False)]))
    t = pd.read_csv(RF / f'DE_{ctx}.csv')
    sym = (t['gene'].astype(str).map(MAPS[ctx]) if ctx in MAPS
           else t['gene'].astype(str).str.upper())
    t['symbol'] = lib_symbols.to_symbols(sym.fillna('')).values
    t = t[t['symbol'] != ''].sort_values('P.Value').drop_duplicates('symbol')
    sel = t[(t['adj.P.Val'] < 0.05) & (t['logFC'] > 0.5)]
    return sorted(set(sel['symbol']))


rows = []
targets = dict(CONTEXTS)
targets['RMC'] = 'renal medullary carcinoma'
for ctx, label in targets.items():
    if ctx != 'RMC' and not (RF / f'DE_{ctx}.csv').exists():
        continue
    genes = up_genes(ctx)
    if len(genes) < 10:
        print(f"  {label:<34} only {len(genes)} up-regulated genes; skipped")
        rows.append({'context': label, 'direction': 'n/a', 'rank': 0,
                     'term': 'insufficient genes for connectivity',
                     'pvalue': None, 'qvalue': None, 'is_nominated_agent': False,
                     'n_up_genes': len(genes)})
        continue
    print(f"  {label:<34} {len(genes):>5} up-regulated genes")
    lid = post_genes(genes[:2000], f'v29 {label}')
    time.sleep(1.0)
    for direction, lib in LIBS.items():
        try:
            res = enrich(lid, lib)
        except Exception as e:
            print(f"      {direction}: FAILED {type(e).__name__}")
            continue
        for rank, item in enumerate(res[:25], 1):
            term = str(item[1])
            rows.append({
                'context': label, 'direction': direction, 'rank': rank,
                'term': term, 'pvalue': item[2], 'qvalue': item[6],
                'is_nominated_agent': any(d in term.lower() for d in NOMINATED),
                'n_up_genes': len(genes)})
        time.sleep(1.0)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(f"\nwrote {len(out)} rows to {OUT}")
sig = out[(out['direction'] == 'reversal') & (out['qvalue'].astype(float) < 0.05)]
print(f"significant reversal terms at q<0.05: {len(sig)}")
hits = out[out['is_nominated_agent'].fillna(False)]
if len(hits):
    print("nominated agents that surfaced:")
    for _, r in hits.iterrows():
        print(f"  {r['context']:<34} {r['direction']:<18} {r['term'][:52]} "
              f"q={r['qvalue']}")
else:
    print("no nominated agent surfaced in any context - the null comparator "
          "of v28 is reproduced on the refit gene lists")
