"""Test the DLL3 gap directly against GSE269750.

The eighteen pre-specified pathway / gene sets were chosen drug-class-first:
each set was included because it contains the target of a clinically developed
drug class. DLL3 is the target of tarlatamab (FDA-approved 2024 for
extensive-stage small-cell lung cancer) and of several DLL3-directed ADCs and
CAR-T programmes, and DLL3 is the canonical ASCL1-lineage surface antigen. By
the framework's own selection logic a DLL3-containing set should therefore have
been in the panel, and its absence is an internal inconsistency rather than a
mere omission.

This script asks the empirical question the manuscript cannot currently answer:
is DLL3 measured in the small-cell bladder cancer cohort, and is it elevated in
the ASCL1-positive subtype?

Writes: results/DLL3_SCBC_CHECK.csv
"""
import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8')

DATA = Path(r"C:\Users\garre\framework_expansion\data\GSE269750_expression.txt.gz")
CALLS = Path(r"C:\Users\garre\framework_expansion\results\SCBC_subtype_calls.csv")
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'results' / 'DLL3_SCBC_CHECK.csv'

with gzip.open(DATA, 'rt') as f:
    expr = pd.read_csv(f, sep='\t', index_col=0)
print(f"expression matrix: {expr.shape[0]} genes x {expr.shape[1]} samples")

calls = pd.read_csv(CALLS, index_col=0)
subtype = calls['subtype']
print("subtype counts:", subtype.value_counts().to_dict())

# Genes of interest: the DLL3/Notch axis plus neuroendocrine context markers
PANEL = ['DLL3', 'ASCL1', 'NEUROD1', 'POU2F3', 'YAP1',
         'NOTCH1', 'NOTCH2', 'HES1', 'HES6', 'INSM1', 'CHGA', 'SYP',
         'SEZ6', 'CEACAM5', 'SSTR2']

present = [g for g in PANEL if g in expr.index]
absent = [g for g in PANEL if g not in expr.index]
print(f"\nmeasured: {present}")
print(f"NOT on platform: {absent}")

rows = []
for gene in present:
    vals = expr.loc[gene]
    for target in ['ASCL1', 'NEUROD1', 'POU2F3', 'YAP1']:
        in_grp = vals[subtype[vals.index] == target].astype(float)
        out_grp = vals[subtype[vals.index] != target].astype(float)
        if len(in_grp) < 2 or len(out_grp) < 2:
            continue
        t, p = stats.ttest_ind(in_grp, out_grp, equal_var=False)
        l2fc = float(np.mean(in_grp) - np.mean(out_grp))  # matrix is log-scale
        rows.append({'gene': gene, 'subtype': target + '+',
                     'n_in': len(in_grp), 'n_out': len(out_grp),
                     'mean_in': round(float(np.mean(in_grp)), 3),
                     'mean_out': round(float(np.mean(out_grp)), 3),
                     'log2FC': round(l2fc, 3),
                     'p': p})

res = pd.DataFrame(rows)
res.to_csv(OUT, index=False)

print("\n" + "=" * 78)
print("DLL3 across lineage subtypes")
print("=" * 78)
d = res[res['gene'] == 'DLL3']
if d.empty:
    print("DLL3 is NOT on this platform - the framework could not have recovered it")
else:
    print(d.to_string(index=False))
    print("\nDLL3 percentile of overall expression, per subtype:")
    dll3 = expr.loc['DLL3'].astype(float)
    for target in ['ASCL1', 'NEUROD1', 'POU2F3', 'YAP1']:
        samples = subtype[subtype == target].index
        samples = [s for s in samples if s in expr.columns]
        if not samples:
            continue
        sub_mean = expr[samples].astype(float).mean(axis=1)
        pct = float((sub_mean < sub_mean['DLL3']).mean() * 100)
        print(f"  {target + '+':<10} mean={sub_mean['DLL3']:.3f}  "
              f"top {100 - pct:.2f}% of transcriptome")

print("\n" + "=" * 78)
print("Comparator: the two targets already in Master Table 1")
print("=" * 78)
print(res[res['gene'].isin(['CEACAM5', 'SSTR2'])].to_string(index=False))
print(f"\nWrote {OUT}")
