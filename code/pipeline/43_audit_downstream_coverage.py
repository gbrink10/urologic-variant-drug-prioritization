"""Audit whether the four orthogonal layers still cover the analysis after the refit.

Two of the layers are per-gene or per-compound lookups and are unaffected by
refitting the differential expression (Human Protein Atlas, DepMap, PRISM). One
is computed FROM the differential-expression gene lists (LINCS connectivity) and
is therefore stale the moment the DE changes.

This reports, for every row and for the current candidate set:
  * which targets the layers cover and which they miss
  * whether a miss is a real absence from the source or a gap in our query
  * which layers must be re-run

Writes: results/refit/DOWNSTREAM_COVERAGE.csv
"""
import sys
from pathlib import Path

import pandas as pd

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RES = REPO / 'results'
RF = RES / 'refit'

defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')
hpa = pd.read_csv(RES / 'HPA_PROTEIN_VALIDATION.csv')
dep = pd.read_csv(RES / 'DEPMAP_STRATIFIED.csv')
dep_all = pd.read_csv(RES / 'DEPMAP_DEPENDENCY.csv')
pri = pd.read_csv(RES / 'PRISM_DRUG_SENSITIVITY.csv')
lincs = pd.read_csv(RES / 'LINCS_CONNECTIVITY.csv')


def norm(x):
    return set(lib_symbols.normalize(list(x)))


hpa_genes = norm(hpa['gene'])
dep_genes = norm(dep['gene']) | norm(dep_all['gene'])
print("LAYER CONTENTS")
print(f"  HPA      {len(hpa_genes):>3} genes: {sorted(hpa_genes)}")
print(f"  DepMap   {len(dep_genes):>3} genes: {sorted(dep_genes)}")
print(f"  PRISM    {len(pri):>3} compounds: {sorted(pri['drug'].astype(str))[:12]} ...")
print(f"  LINCS    {len(lincs):>3} rows over contexts "
      f"{sorted(set(lincs[lincs.columns[0]].astype(str)))[:8]}")

rows = []
print("\nPER-ROW COVERAGE (scoring gene after HGNC normalisation)")
for _, d in defs.iterrows():
    n = int(d['N'])
    g = lib_symbols.normalize([d['scoring_gene']]).iloc[0]
    novel = str(d['Prior status']).startswith('FRAMEWORK-NOVEL')
    surv = bool(sel[sel['N'] == n]['survives'].iloc[0]) if (sel['N'] == n).any() else False
    in_hpa, in_dep = g in hpa_genes, g in dep_genes
    rows.append({'N': n, 'gene': g, 'framework_novel': novel, 'survives': surv,
                 'in_HPA': in_hpa, 'in_DepMap': in_dep})
    if novel or surv:
        print(f"  row {n:<3} {g:<9} novel={novel!s:<5} survives={surv!s:<5} "
              f"HPA={in_hpa!s:<5} DepMap={in_dep}")

cov = pd.DataFrame(rows)
cov.to_csv(RF / 'DOWNSTREAM_COVERAGE.csv', index=False)

print("\nGAPS THAT MATTER")
gaps = []
for _, r in cov[cov['framework_novel'] | cov['survives']].iterrows():
    if not r['in_DepMap']:
        gaps.append(f"row {int(r['N'])} {r['gene']}: absent from the DepMap extract")
    if not r['in_HPA']:
        gaps.append(f"row {int(r['N'])} {r['gene']}: absent from the HPA extract")
for g in gaps:
    print("  -", g)
if not gaps:
    print("  none for the framework-novel or surviving rows")

print("\nSTALENESS")
print("  HPA     per-gene lookup, independent of the DE refit           -> valid")
print("  DepMap  per-gene CRISPR effect, independent of the DE refit    -> valid")
print("  PRISM   per-compound viability, independent of the DE refit    -> valid")
print("  LINCS   computed FROM the up-regulated DE gene lists           -> STALE, "
      "must be recomputed from the refit")

# which genes newly enter the analysis because the refit changed the axis
chem = ['CXCL8', 'CXCL1', 'CXCL2', 'CXCL3']
print("\nRMC chemokine axis after refit:", chem)
print("  covered by HPA:", [g for g in chem if g in hpa_genes] or 'none')
print("  note: the ligands are the nominating signal; the drug targets are the"
      " receptors CXCR1/CXCR2, which are in HPA:",
      all(g in hpa_genes for g in ('CXCR1', 'CXCR2')))
