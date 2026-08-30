"""Add Benjamini-Hochberg FDR q-values to the KEGG / gene-set enrichment output.

The 9-point Molecular Prioritization Score uses a NOMINAL upper-tail
hypergeometric p-value threshold (p < 0.10) for its pathway component.
This script computes, in addition, the Benjamini-Hochberg q-value across
the 18 pre-specified pathway / gene sets WITHIN each clinical context, so
that both the nominal p used for scoring and the multiplicity-corrected q
are reported side by side in the deposited table and in the manuscript.

Writes: results/KEGG_ENRICHMENT_ALL10.csv (adds `qvalue_BH` column)
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

REPO = Path(__file__).resolve().parents[2]
TARGETS = [REPO / 'results' / 'KEGG_ENRICHMENT_ALL10.csv']


def bh_qvalues(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg step-up FDR q-values."""
    p = np.asarray(p, dtype=float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]      # enforce monotonicity
    out = np.empty(n, dtype=float)
    out[order] = np.clip(q, 0, 1)
    return out


for path in TARGETS:
    df = pd.read_csv(path)
    # BH correction is applied across the 18 pathway / gene sets within each
    # context (the family of tests actually performed per clinical context).
    df['qvalue_BH'] = (df.groupby('context')['pvalue']
                         .transform(lambda s: bh_qvalues(s.values)))
    df.to_csv(path, index=False)
    print(f"Wrote {path}  ({len(df)} rows, {df['context'].nunique()} contexts)")

    print("\nPathways with nominal p < 0.10, per context:")
    for ctx, sub in df[df['pvalue'] < 0.10].groupby('context'):
        for _, r in sub.sort_values('pvalue').iterrows():
            flag = 'survives BH q<0.10' if r['qvalue_BH'] < 0.10 else 'does NOT survive BH'
            print(f"  {ctx:<14} {r['pathway']:<34} "
                  f"k={int(r['overlap_k']):<2} p={r['pvalue']:.3g}  "
                  f"q_BH={r['qvalue_BH']:.3g}   [{flag}]")
