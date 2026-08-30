"""Score DLL3 in ASCL1+ small-cell bladder cancer by the framework's own rules,
and test whether a Notch gene set would have been enriched had it been included
in the pre-specified panel.

Rationale: the panel was assembled drug-class-first, and DLL3 is the target of
an FDA-approved agent (tarlatamab, 2024). Its exclusion is therefore an internal
inconsistency in the selection logic, not a deliberate scope decision. This
script quantifies what the framework would have produced had the set been present.

Writes: results/DLL3_CANDIDATE_ROW.csv
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import hypergeom

sys.stdout.reconfigure(encoding='utf-8')

DATA = Path(r"C:\Users\garre\framework_expansion\data\GSE269750_expression.txt.gz")
CALLS = Path(r"C:\Users\garre\framework_expansion\results\SCBC_subtype_calls.csv")
KEGG = Path(r"C:\Users\garre\framework_expansion\results\kegg_pathways.json")
REPO = Path(__file__).resolve().parents[2]

with gzip.open(DATA, 'rt') as f:
    expr = pd.read_csv(f, sep='\t', index_col=0)
subtype = pd.read_csv(CALLS, index_col=0)['subtype']


def bh(p):
    p = np.asarray(p, float)
    n = p.size
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.clip(q, 0, 1)
    return out


# ---- full transcriptome DE for ASCL1+ vs other subtypes -------------------
cols = [c for c in expr.columns if c in subtype.index]
in_cols = [c for c in cols if subtype[c] == 'ASCL1']
out_cols = [c for c in cols if subtype[c] != 'ASCL1']
print(f"ASCL1+ n={len(in_cols)}  vs others n={len(out_cols)}")

A = expr[in_cols].astype(float)
B = expr[out_cols].astype(float)
t, p = stats.ttest_ind(A, B, axis=1, equal_var=False)
de = pd.DataFrame({'gene': expr.index,
                   'log2FC': A.mean(axis=1).values - B.mean(axis=1).values,
                   'p': p}).dropna()
de['q'] = bh(de['p'].values)
de = de.sort_values('q')

row = de[de['gene'] == 'DLL3'].iloc[0]
rank_pct = float((de['log2FC'] > row['log2FC']).mean() * 100)
print(f"\nDLL3 in ASCL1+ SCBC: log2FC={row['log2FC']:+.3f}  "
      f"p={row['p']:.4g}  BH q={row['q']:.4g}")
print(f"  fold-change rank: top {rank_pct:.2f}% of {len(de)} measured transcripts")

# ---- E component by the published bins ------------------------------------
# The manuscript is ambiguous about what "significant" means for this component:
# the candidate-generation criteria state p < 0.05, while every audited row in
# Master Table 1 also satisfies q < 0.05. Both readings are reported here rather
# than silently picking the flattering one.
significant_nominal = row['p'] < 0.05
significant_fdr = row['q'] < 0.05
top_one_pct = rank_pct < 1.0


def e_component(sig):
    if (sig and abs(row['log2FC']) >= 1) or top_one_pct:
        return 3
    if sig and abs(row['log2FC']) >= 0.5:
        return 2
    if sig:
        return 1
    return 0


E_nominal = e_component(significant_nominal)
E_fdr = e_component(significant_fdr)
E = E_fdr          # the conservative reading is carried forward
print(f"  nominally significant (p<0.05): {significant_nominal} -> E={E_nominal}")
print(f"  survives BH (q<0.05):           {significant_fdr} -> E={E_fdr}")
print(f"  top 1% by fold change:          {top_one_pct}")
print(f"  E carried forward (conservative): {E}")

# ---- would a Notch set have been enriched? --------------------------------
kegg = json.load(open(KEGG))
print(f"\npre-specified sets in panel: {len(kegg)}")
print("Notch present in panel?",
      any('otch' in k for k in kegg))

# KEGG hsa04330 Notch signalling pathway membership
NOTCH = ['DLL1', 'DLL3', 'DLL4', 'DTX1', 'DTX2', 'DTX3', 'DTX3L', 'DTX4',
         'DVL1', 'DVL2', 'DVL3', 'HES1', 'HES5', 'HEYL', 'JAG1', 'JAG2',
         'LFNG', 'MFNG', 'RFNG', 'NCOR2', 'NOTCH1', 'NOTCH2', 'NOTCH3',
         'NOTCH4', 'PSEN1', 'PSEN2', 'PSENEN', 'RBPJ', 'RBPJL', 'SNW1',
         'CTBP1', 'CTBP2', 'CREBBP', 'EP300', 'HDAC1', 'HDAC2', 'KAT2A',
         'KAT2B', 'MAML1', 'MAML2', 'MAML3', 'NUMB', 'NUMBL', 'ADAM17',
         'APH1A', 'APH1B', 'NCSTN']

up = set(de[(de['p'] < 0.05) & (de['log2FC'] >= 0.5)]['gene'])
universe = 20000
K = len(set(NOTCH))
n = len(up)
k = len(up & set(NOTCH))
p_notch = hypergeom.sf(k - 1, universe, K, n) if k else 1.0
print(f"\nNotch set (hsa04330): K={K}, ASCL1+ up-set n={n}, overlap k={k}")
print(f"  overlap genes: {sorted(up & set(NOTCH))}")
print(f"  upper-tail hypergeometric p = {p_notch:.4g}")

target_in_pathway = 'DLL3' in NOTCH
enriched = p_notch < 0.10
P = 2 if (enriched and target_in_pathway) else (1 if (enriched or target_in_pathway) else 0)
print(f"  P component = {P} (enriched at p<0.10: {enriched}; "
      f"target in set: {target_in_pathway})")

# ---- assemble the candidate row -------------------------------------------
G = 1   # same context anchor used for rows 28-30 (TP53/RB1 near-universal in SCBC)
L = 1   # tarlatamab + DLL3/ASCL1 biology extensively published in SCLC
def tier_of(x):
    return 'Strong' if x >= 7 else 'Moderate' if x >= 4 else 'Exploratory'


total = G + E + P + L
total_nominal = G + E_nominal + P + L
tier = tier_of(total)
print(f"\nCandidate row (conservative, q<0.05): G={G} E={E} P={P} L={L} "
      f"-> {total}/9 - {tier} tier")
print(f"Candidate row (nominal, p<0.05):      G={G} E={E_nominal} P={P} L={L} "
      f"-> {total_nominal}/9 - {tier_of(total_nominal)} tier")
print("\nNOTE: DLL3/tarlatamab in genitourinary small-cell carcinoma is already "
      "proposed in\nthe urologic-oncology literature (Liao 2024, ASCO Educ Book "
      "44:e430336, PMID 38176691),\nand tarlatamab is in trial for extrapulmonary "
      "small-cell carcinoma (NCT06816394).\nBy the manuscript's urologic-only "
      "novelty standard this is therefore a PREVIOUSLY\nPROPOSED priority that the "
      "pre-specified pathway panel failed to surface.")

pd.DataFrame([{
    'context': 'SCBC (ASCL1+)',
    'drug': 'Tarlatamab (DLL3 x CD3 bispecific T-cell engager)',
    'target': 'DLL3',
    'log2FC': round(float(row['log2FC']), 3),
    'p': float(row['p']),
    'q_BH': float(row['q']),
    'fold_change_rank_pct': round(rank_pct, 2),
    'G': G, 'E_conservative_q': E, 'E_nominal_p': E_nominal, 'P': P, 'L': L,
    'total_conservative': total, 'tier_conservative': tier,
    'total_nominal': total_nominal, 'tier_nominal': tier_of(total_nominal),
    'prior_status': 'PREVIOUSLY PROPOSED in urologic-oncology literature '
                    '(Liao 2024 ASCO Educ Book, PMID 38176691); not recovered '
                    'by the pre-specified 18-set panel',
    'notch_set_hypergeom_p': float(p_notch),
    'notch_overlap_k': k,
}]).to_csv(REPO / 'results' / 'DLL3_CANDIDATE_ROW.csv', index=False)
print(f"\nWrote {REPO / 'results' / 'DLL3_CANDIDATE_ROW.csv'}")
