"""Biomarker- and expression-stratified DepMap dependency analysis.

24_depmap_dependency.py averaged gene effect across all urothelial lines
regardless of genotype or target expression. That is the wrong test for a
biomarker-matched framework, and it shows: FGFR3 scores as "not a dependency"
on the lineage average even though erdafitinib is approved in FGFR3-altered
urothelial cancer, because the dependency exists only in the altered subset.
The lineage average therefore under-calls true dependencies, which is the same
direction that would produce a false negative for an expression-nominated target.

This script repeats the analysis the way the framework nominates:

  * targets nominated on MUTATION or DELETION (FGFR3, PIK3CA, CDKN2A-driven
    CDK4/6) are split mutant vs wild-type;
  * targets nominated on EXPRESSION (NSD2, G6PD, EZH2, BCL2, ATR/ATRIP, PTGS1,
    DNMT1, AURKA) are split high- vs low-expressing, since the hypothesis in
    those rows is that cells over-expressing the target depend on it.

Genotype and expression come from CCLE via the cBioPortal API (the DepMap portal
is bot-gated and the release omics files are not mirrored on figshare); gene
effect comes from the DepMap 24Q4 CRISPR screen. Cell lines are joined on
normalised name.

Writes: results/DEPMAP_STRATIFIED.csv
"""
import json
import sys
import urllib.request
from pathlib import Path

import paths

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
SCRATCH = paths.DATA / 'cache'   # large third-party downloads; see README for how to populate
CRISPR = SCRATCH / 'CRISPRGeneEffect.csv'
LINES = REPO / 'results' / 'DEPMAP_CELL_LINES.csv'
OUT = REPO / 'results' / 'DEPMAP_STRATIFIED.csv'

API = "https://www.cbioportal.org/api"
STUDY = "ccle_broad_2025"
EXPR_PROFILE = f"{STUDY}_rna_seq_mrna"
MUT_PROFILE = f"{STUDY}_mutations"
CNA_PROFILE = f"{STUDY}_log2CNA"

# gene -> (rows, how the framework nominated it, stratifying feature)
TARGETS = {
    'NSD2':    ('23', 'expression', 'NSD2'),
    'G6PD':    ('26', 'expression', 'G6PD'),
    'ATR':     ('24', 'expression', 'ATRIP'),
    'ATRIP':   ('24', 'expression', 'ATRIP'),
    'EZH2':    ('3',  'expression', 'EZH2'),
    'BCL2':    ('1',  'expression', 'BCL2'),
    'DNMT1':   ('4',  'expression', 'DNMT1'),
    'AURKA':   ('2, 7', 'expression', 'AURKA'),
    'PTGS1':   ('30', 'expression', 'PTGS1'),
    'EPAS1':   ('15', 'expression', 'EPAS1'),
    'FGFR3':   ('10', 'mutation', 'FGFR3'),
    'PIK3CA':  ('9',  'mutation', 'PIK3CA'),
    'CDK4':    ('13, 16', 'deletion', 'CDKN2A'),
    'CDK6':    ('13, 16', 'deletion', 'CDKN2A'),
}


def post(path, body):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def get(path):
    req = urllib.request.Request(API + path, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def norm(name):
    return ''.join(ch for ch in str(name).upper() if ch.isalnum())


# ---- urothelial lines: DepMap ACH <-> CCLE sample id ------------------------
lines_df = pd.read_csv(LINES)
uro = lines_df[lines_df['context'] == 'urothelial'].dropna(subset=['cell_line'])
by_norm = {norm(n): a for n, a in zip(uro['cell_line'], uro['ModelID'])}

samples = get(f"/studies/{STUDY}/samples?pageSize=3000")
ccle_uro = {}
for s in samples:
    sid = s['sampleId']
    prefix = sid.split('_')[0]
    if norm(prefix) in by_norm:
        ccle_uro[sid] = by_norm[norm(prefix)]
print(f"urothelial lines matched between Cellosaurus/DepMap and CCLE: {len(ccle_uro)}")

sample_ids = list(ccle_uro)
genes = sorted({g for g in TARGETS} | {v[2] for v in TARGETS.values()})
gene_recs = post("/genes/fetch?geneIdType=HUGO_GENE_SYMBOL", genes)
entrez = {g['hugoGeneSymbol']: g['entrezGeneId'] for g in gene_recs}
print(f"resolved entrez ids for {len(entrez)} genes")

# ---- pull expression, mutation and copy number -----------------------------
def fetch_molecular(profile):
    return post(f"/molecular-profiles/{profile}/molecular-data/fetch?projection=SUMMARY",
                {'entrezGeneIds': list(entrez.values()), 'sampleIds': sample_ids})


expr = pd.DataFrame(fetch_molecular(EXPR_PROFILE))
cna = pd.DataFrame(fetch_molecular(CNA_PROFILE))
muts = pd.DataFrame(post(
    f"/molecular-profiles/{MUT_PROFILE}/mutations/fetch?projection=DETAILED",
    {'entrezGeneIds': list(entrez.values()), 'sampleIds': sample_ids}))
print(f"expression rows {len(expr)} | CNA rows {len(cna)} | mutation rows {len(muts)}")

# ---- DepMap gene effect ----------------------------------------------------
header = pd.read_csv(CRISPR, nrows=0)
col_for = {}
for col in header.columns:
    sym = col.split(' (')[0].strip()
    if sym in TARGETS and sym not in col_for:
        col_for[sym] = col
eff = pd.read_csv(CRISPR, usecols=[header.columns[0]] + list(col_for.values()))
eff = eff.rename(columns={header.columns[0]: 'ModelID'})
eff = eff.rename(columns={v: k for k, v in col_for.items()})
eff = eff.set_index('ModelID')

ach_for_sample = ccle_uro
rows = []
for gene, (mtrows, mode, feature) in TARGETS.items():
    if gene not in eff.columns:
        rows.append({'gene': gene, 'rows': mtrows, 'stratified_by': mode,
                     'feature': feature, 'verdict': 'gene not in DepMap release'})
        continue

    # assign each matched line to the positive or negative stratum
    pos, neg = [], []
    for sid, ach in ach_for_sample.items():
        if ach not in eff.index or pd.isna(eff.at[ach, gene]):
            continue
        if mode == 'mutation':
            hit = not muts.empty and (
                (muts['sampleId'] == sid) &
                (muts['gene'].apply(lambda g: g.get('hugoGeneSymbol') == feature
                                    if isinstance(g, dict) else False))).any()
        elif mode == 'deletion':
            sub = cna[(cna['sampleId'] == sid) &
                      (cna['entrezGeneId'] == entrez.get(feature))]
            hit = (not sub.empty) and float(sub['value'].iloc[0]) < -0.5
        else:                                   # expression
            sub = expr[(expr['sampleId'] == sid) &
                       (expr['entrezGeneId'] == entrez.get(feature))]
            hit = None if sub.empty else float(sub['value'].iloc[0])
        (pos if hit else neg).append((ach, hit))

    if mode == 'expression':
        vals = [(a, v) for a, v in pos + neg if v is not None]
        if len(vals) < 8:
            rows.append({'gene': gene, 'rows': mtrows, 'stratified_by': mode,
                         'feature': feature, 'verdict': 'too few lines with expression'})
            continue
        cut = np.percentile([v for _, v in vals], 66.7)
        hi = [eff.at[a, gene] for a, v in vals if v >= cut]
        lo = [eff.at[a, gene] for a, v in vals if v < cut]
        label_hi, label_lo = f'{feature}-high', f'{feature}-low'
    else:
        hi = [eff.at[a, gene] for a, h in pos if a in eff.index]
        lo = [eff.at[a, gene] for a, h in neg if a in eff.index]
        label_hi = f'{feature}-altered'
        label_lo = f'{feature}-wildtype'

    hi = [x for x in hi if pd.notna(x)]
    lo = [x for x in lo if pd.notna(x)]
    if len(hi) < 3 or len(lo) < 3:
        # Why a stratum can come up empty, recorded rather than left blank:
        #   FGFR3 - the FGFR3 alterations that define erdafitinib sensitivity in
        #     urothelial lines are predominantly FGFR3-TACC3 fusions, which the
        #     cBioPortal mutation profile does not carry; no point mutation is
        #     found in any of the 37 matched lines.
        #   CDKN2A - the log2CNA profile returns only non-negative values for
        #     these lines (median 0.53), so it cannot support a homozygous
        #     deletion call at any sensible threshold.
        reason = {
            'FGFR3': 'not testable - FGFR3 alterations in urothelial lines are '
                     'mainly TACC3 fusions, absent from the mutation profile',
            'CDKN2A': 'not testable - copy-number profile carries no negative '
                      'values for these lines, so deletion cannot be called',
        }.get(feature, 'stratum too small to test')
        rows.append({'gene': gene, 'rows': mtrows, 'stratified_by': mode,
                     'feature': feature, 'n_positive': len(hi), 'n_negative': len(lo),
                     'verdict': reason})
        continue

    p = float(stats.mannwhitneyu(hi, lo, alternative='less').pvalue)
    rows.append({
        'gene': gene, 'rows': mtrows, 'stratified_by': mode, 'feature': feature,
        'positive_stratum': label_hi, 'negative_stratum': label_lo,
        'n_positive': len(hi), 'n_negative': len(lo),
        'mean_effect_positive': round(float(np.mean(hi)), 3),
        'mean_effect_negative': round(float(np.mean(lo)), 3),
        'difference': round(float(np.mean(hi) - np.mean(lo)), 3),
        'p_one_sided': f'{p:.3g}',
        'pct_positive_dependent': round(float(np.mean(np.array(hi) < -0.5) * 100), 1),
        'verdict': ('selective dependency in the nominated stratum'
                    if (np.mean(hi) < -0.5 and p < 0.05)
                    else 'dependency in stratum but not selective'
                    if np.mean(hi) < -0.5
                    else 'no dependency in the nominated stratum'),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
cols = ['gene', 'rows', 'stratified_by', 'n_positive', 'n_negative',
        'mean_effect_positive', 'mean_effect_negative', 'p_one_sided', 'verdict']
print("\n" + out[[c for c in cols if c in out.columns]].to_string(index=False))
print(f"\nWrote {OUT}")
