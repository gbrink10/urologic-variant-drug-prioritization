"""Cross-check the Python moderated-t implementation against Bioconductor limma.

lib_limma.py was written before R was available on the analysis machine and was
validated against analytic behaviour, but agreement with limma itself had not
been tested on real data. Two independent implementations agreeing on the
deposited matrices is a stronger reproducibility claim than either alone, and a
disagreement would mean one of them is wrong.

Runs the same design through both engines on the log-scale contexts and reports
the correlation of log-fold changes, of moderated t statistics, and the overlap
of the significant gene sets.

Writes: results/refit/PYTHON_R_CROSSCHECK.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import lib_limma

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
PREP = REPO / 'data' / 'prepared'

# SarcUC is the like-for-like comparison: both engines fit the same ~ group
# design. PSCC is deliberately NOT like-for-like - the deposited R fit blocks on
# donor by duplicate correlation, which the Python implementation does not
# support - so the gap there measures what ignoring the technical replicates
# would have bought, which is the reason the blocking is in the analysis.
CASES = [
    ('SarcUC', 'group', 'UC', 'SARC', True),
    ('PSCC', 'group', 'Normal', 'Tumor', False),
]

rows = []
for ctx, col, ref, alt, like_for_like in CASES:
    E = pd.read_csv(PREP / f'{ctx}_expr.csv', index_col=0)
    M = pd.read_csv(PREP / f'{ctx}_meta.csv')
    grp = M[col].astype(str).values
    keep = E.notna().all(axis=1) & (E.var(axis=1) > 0)
    E = E[keep]

    design = np.column_stack([np.ones(len(grp)), (grp == alt).astype(float)])
    fit = lib_limma.lm_fit(E.values, design)
    res = lib_limma.ebayes(fit, coef=1)
    py = pd.DataFrame({'gene': E.index, 'logFC_py': res['logFC'],
                       't_py': res['t'], 'q_py': res['q_value']})

    r = pd.read_csv(RF / f'DE_{ctx}.csv')[['gene', 'logFC', 't', 'adj.P.Val']]
    r.columns = ['gene', 'logFC_r', 't_r', 'q_r']
    m = py.merge(r, on='gene')
    m = m[np.isfinite(m['t_py']) & np.isfinite(m['t_r'])]

    fc_r = float(np.corrcoef(m['logFC_py'], m['logFC_r'])[0, 1])
    t_r_ = float(np.corrcoef(m['t_py'], m['t_r'])[0, 1])
    sig_py = set(m.loc[m['q_py'] < 0.05, 'gene'])
    sig_r = set(m.loc[m['q_r'] < 0.05, 'gene'])
    jac = len(sig_py & sig_r) / max(1, len(sig_py | sig_r))
    max_fc_diff = float((m['logFC_py'] - m['logFC_r']).abs().max())

    rows.append({'context': ctx, 'like_for_like': like_for_like,
                 'n_genes': len(m),
                 'logFC_correlation': round(fc_r, 6),
                 'max_abs_logFC_difference': round(max_fc_diff, 8),
                 't_correlation': round(t_r_, 6),
                 'n_sig_python': len(sig_py), 'n_sig_R': len(sig_r),
                 'jaccard_significant': round(jac, 4)})
    print(f"  {ctx}: {len(m):,} genes")
    print(f"    log-fold change  r = {fc_r:.6f}   max |difference| = {max_fc_diff:.2e}")
    print(f"    moderated t      r = {t_r_:.6f}")
    print(f"    significant at q<0.05  python {len(sig_py):,}  R {len(sig_r):,}  "
          f"Jaccard {jac:.3f}")

out = pd.DataFrame(rows)
out.to_csv(RF / 'PYTHON_R_CROSSCHECK.csv', index=False)
lfl = out[out['like_for_like']]
agree = bool((lfl['logFC_correlation'] > 0.9999).all()
             and (lfl['t_correlation'] > 0.99).all()
             and (lfl['jaccard_significant'] > 0.95).all())
print(f"\nlike-for-like designs agree: {agree}")
for _, r in out[~out['like_for_like']].iterrows():
    infl = r['n_sig_python'] / max(1, r['n_sig_R'])
    print(f"  {r['context']}: the unblocked model calls {r['n_sig_python']:,} "
          f"features significant against {r['n_sig_R']:,} when donor is "
          f"modelled as a blocking factor, a {infl:.1f}x inflation from "
          f"treating technical replicates as independent samples")
print(f"wrote {RF / 'PYTHON_R_CROSSCHECK.csv'}")
