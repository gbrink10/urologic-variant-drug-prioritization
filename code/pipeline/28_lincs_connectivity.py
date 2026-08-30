"""Connectivity (signature-reversal) analysis against LINCS L1000.

The classical computational-repurposing method asks a different question from
anything else in this study: not whether a target is expressed, required, or
druggable, but whether a compound's transcriptional signature REVERSES the
disease signature. It is the standard comparator in the drug-repurposing
literature and its absence would be a fair criticism of this manuscript.

Method. For each disease context we take the significantly up-regulated gene set
and test it against the LINCS L1000 chemical-perturbation libraries through the
Enrichr API:

  * enrichment in LINCS_L1000_Chem_Pert_down means the compound DOWN-regulates
    the genes that are UP in the disease - signature reversal, the therapeutic
    direction;
  * enrichment in LINCS_L1000_Chem_Pert_up means the compound reproduces the
    disease signature - the opposite direction, reported as an internal control
    so that a compound appearing in both can be recognised as non-specific.

This is a hypothesis-generating comparator, not evidence of efficacy: L1000
signatures are measured in whichever cell lines the LINCS project profiled, none
of which are the rare histologies studied here.

Writes: results/LINCS_CONNECTIVITY.csv
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
DE = REPO / 'data' / 'DE_results' / 'FULL_DE_RESULTS_ALL10.csv'
OUT = REPO / 'results' / 'LINCS_CONNECTIVITY.csv'
BASE = "https://maayanlab.cloud/Enrichr"

LIBS = {'reversal': 'LINCS_L1000_Chem_Pert_down',
        'mimicry (control)': 'LINCS_L1000_Chem_Pert_up'}

# nominated agents, to check whether the framework's own candidates surface
NOMINATED = ['reparixin', 'navarixin', 'azd5069', 'danirixin', 'ladarixin',
             'erlotinib', 'ceralasertib', 'berzosertib', 'celecoxib', 'aspirin',
             'venetoclax', 'alisertib', 'tazemetostat', 'decitabine',
             'azacitidine', 'olaparib', 'talazoparib', 'alpelisib', 'erdafitinib',
             'palbociclib', 'abemaciclib', 'pazopanib', 'marimastat', 'polydatin',
             'bortezomib']


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


# ---- build the up-regulated gene set for each context ----------------------
de = pd.read_csv(DE)
de['sym'] = de['gene_symbol'].astype(str).str.upper()
CONTEXTS = {
    'renal medullary carcinoma': 'RMC',
    'penile squamous cell carcinoma': 'Penile SCC',
    'sarcomatoid urothelial carcinoma': 'Sarcomatoid UC',
    'SCBC ASCL1+': 'SCBC ASCL1+ subtype',
    'SCBC NEUROD1+': 'SCBC NEUROD1+ subtype',
    'SCBC POU2F3+': 'SCBC POU2F3+ subtype',
}

rows = []
for label, ctx in CONTEXTS.items():
    sub = de[de['context'] == ctx].copy()
    if sub.empty:
        print(f"{label:<34} no rows in deposited DE table")
        continue
    sub = sub[sub['log2FC_disease_state'] > 0]
    if 'qvalue' in sub.columns:
        sig = sub[(sub['qvalue'] < 0.05) | sub['qvalue'].isna()]
        sub = sig if len(sig) >= 10 else sub
    genes = (sub.sort_values('log2FC_disease_state', ascending=False)['sym']
             .dropna().drop_duplicates().head(250).tolist())
    genes = [g for g in genes if g and g != 'NAN']
    if len(genes) < 5:
        print(f"{label:<34} only {len(genes)} genes - skipped")
        continue

    lid = post_genes(genes, f'{label} up-regulated')
    time.sleep(1)
    print(f"{label:<34} {len(genes):>4} up genes submitted")

    for direction, lib in LIBS.items():
        try:
            res = enrich(lid, lib)
        except Exception as exc:                                # noqa: BLE001
            print(f"   {lib}: FAILED {exc}")
            continue
        for rank, r in enumerate(res[:60], 1):
            term, p, _, _, adj = r[1], r[2], r[3], r[4], r[6]
            low = term.lower()
            rows.append({
                'context': label, 'direction': direction, 'library': lib,
                'rank': rank, 'term': term, 'p_value': p, 'adj_p_value': adj,
                'overlap_genes': ';'.join(r[5][:12]),
                'matches_nominated_agent': next(
                    (d for d in NOMINATED if d in low), None),
            })
        time.sleep(1)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print(f"\n{len(out)} enrichment rows written")
rev = out[(out['direction'] == 'reversal') & (out['adj_p_value'] < 0.05)]
print(f"significant reversal terms (adj p < 0.05): {len(rev)}")

print("\n--- top reversal hits per context ---")
for ctx in out['context'].unique():
    sub = out[(out['context'] == ctx) & (out['direction'] == 'reversal')].head(5)
    print(f"\n{ctx}")
    for _, r in sub.iterrows():
        flag = f"  <== {r['matches_nominated_agent']}" if r['matches_nominated_agent'] else ''
        print(f"   {r['rank']:>2}. {r['term'][:66]:<68} adj p={r['adj_p_value']:.3g}{flag}")

hits = out[out['matches_nominated_agent'].notna()]
print(f"\n--- nominated agents appearing anywhere in the top 60 ---")
if hits.empty:
    print("   none")
else:
    for _, r in hits.iterrows():
        print(f"   {r['context']:<32} {r['direction']:<18} {r['term'][:52]:<54} "
              f"adj p={r['adj_p_value']:.3g}")
print(f"\nWrote {OUT}")
