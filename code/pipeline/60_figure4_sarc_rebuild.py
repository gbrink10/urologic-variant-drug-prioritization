"""Rebuild Figure 4 around the data the sarcomatoid rows are actually scored on.

The figure it replaces spent two of three panels on a comparison the paper says
cannot be interpreted: the chip-aligned group separation and the pathway values
that inherit its confounding. That is a lot of a main-text display item spent
showing what was not used.

What was used is within-sarcomatoid abundance, and there is a positive result
in it that the old figure never showed. The 28 sarcomatoid tumors sit on four
independent chip batches, so the abundance ranking can be recomputed inside
each batch on its own. It holds in all four, which is what rules out the
ranking being a batch artifact - the very worry the confounded contrast raises.

Panel A places the four scoring genes in the sarcomatoid transcriptome. Panel B
recomputes each one independently within each chip batch. The confounded
contrast moves to the Supplementary Results, where the paper already reports
the sarcomatoid series in full.

Every percentile here is computed by the same route 39_rescore_from_refit.py
uses for the score: probes mapped to symbols, collapsed by maximum, restricted
to the sarcomatoid samples, then ranked against the same 20,363-gene universe.
The pooled values reproduce SCORING_PROVENANCE_V29.csv exactly, and the script
asserts that before it draws anything.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_symbols
import paths

REPO = Path(__file__).resolve().parents[2]
PREP = REPO / 'data' / 'prepared'
FIG = REPO / 'figures'
RF = REPO / 'results' / 'refit'

plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 9,
                     'axes.linewidth': 0.8})

GENES = ('UHRF1', 'NSD2', 'G6PD', 'ATR')
THRESH = 85.0          # the abundance route scores against the 85th percentile
DARK, WARM, GREY = '#1a3a5c', '#a93226', '#8d99a6'


def gene_level_sarcomatoid():
    """The matrix the score is computed from: probes to symbols, collapsed by
    maximum, restricted to the sarcomatoid tumors."""
    mp = pd.read_csv(REPO / 'data' / 'DE_results' / 'SarcomatoidUC_DE_full.csv.gz')
    m = dict(zip(mp['probe_id'].astype(str), mp['gene'].astype(str).str.upper()))
    e = pd.read_csv(PREP / 'SarcUC_expr.csv', index_col=0)
    meta = pd.read_csv(PREP / 'SarcUC_meta.csv')
    sym = pd.Series([m.get(str(i), '') for i in e.index], index=e.index)
    sym = pd.Series(lib_symbols.normalize(sym).values, index=e.index)
    e = e[sym.values != '']
    e = e.groupby(sym[sym.values != ''].values).max()
    sarc = [s for s in meta.loc[meta['group'] == 'SARC', 'sample'] if s in e.columns]
    chip = {str(k): str(v) for k, v in zip(meta['sample'], meta['chip'])}
    return e[sarc], sarc, chip


def ordinal(v):
    """91 -> '91st'. A hardcoded 'th' suffix has bitten this figure before."""
    i = int(round(v))
    suf = ('th' if 10 <= i % 100 <= 20
           else {1: 'st', 2: 'nd', 3: 'rd'}.get(i % 10, 'th'))
    return f'{i}{suf}'


def pct_of(means, gene):
    return float((means < means[gene]).mean() * 100)


expr, sarc, chip = gene_level_sarcomatoid()
chips = sorted({chip[s] for s in sarc})
pooled_mean = expr.mean(axis=1)
pooled = {g: pct_of(pooled_mean, g) for g in GENES}

# the figure must not disagree with the deposited score
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
import re
for n_, g in ((25, 'UHRF1'), (23, 'NSD2'), (26, 'G6PD'), (24, 'ATR')):
    basis = str(prov.loc[prov['N'] == n_, 'E_basis'].iloc[0])
    want = float(re.search(r'at ([0-9.]+)th percentile', basis).group(1))
    assert abs(want - pooled[g]) < 0.15, (g, want, pooled[g])
UNIVERSE = len(pooled_mean)

per_chip = {g: {c: pct_of(expr[[s for s in sarc if chip[s] == c]].mean(axis=1), g)
                for c in chips} for g in GENES}
n_per_chip = {c: sum(1 for s in sarc if chip[s] == c) for c in chips}

fig = plt.figure(figsize=(11.0, 4.6))
gs = gridspec.GridSpec(1, 2, width_ratios=[1.0, 1.02], wspace=0.30,
                       left=0.085, right=0.985, top=0.80, bottom=0.15)

# ---- A: where the scoring genes sit in the sarcomatoid transcriptome ----
axA = fig.add_subplot(gs[0, 0])
vals = np.sort(pooled_mean.values)
q = np.linspace(0, 100, len(vals))
axA.plot(q, vals, lw=1.4, color=GREY, zorder=1)
axA.axvline(THRESH, ls='--', lw=0.9, c='#888', zorder=2)
axA.text(THRESH - 1.5, vals.min() + (vals.max() - vals.min()) * 0.02,
         'top 15%', fontsize=7.2, color='#666', style='italic',
         ha='right', va='bottom')
# G6PD and NSD2 are five percentiles apart, so their labels need opposite sides
OFF = {'UHRF1': (2, 12), 'NSD2': (16, -4), 'G6PD': (-24, 2), 'ATR': (-2, -18)}
for g in GENES:
    p = pooled[g]
    yv = float(pooled_mean[g])
    c = DARK if p >= THRESH else WARM
    axA.scatter([p], [yv], s=62, color=c, edgecolor='white', linewidth=1.0,
                zorder=4)
    axA.annotate(f'{g}\n{ordinal(p)}', (p, yv), textcoords='offset points',
                 xytext=OFF[g], fontsize=7.6, weight='bold', color=c,
                 ha='center')
axA.set_xlim(0, 103)
axA.set_xlabel(f'percentile of the {UNIVERSE:,} genes measured in these tumors',
               fontsize=8.6)
axA.set_ylabel('log$_2$ expression, mean across the 28 tumors', fontsize=8.6)
axA.set_title('A. What these rows are scored on\n'
              'abundance within the sarcomatoid tumors',
              fontsize=9.6, weight='bold', loc='left')
axA.tick_params(labelsize=8.0)
for s_ in ('top', 'right'):
    axA.spines[s_].set_visible(False)

# ---- B: the same ranking recomputed inside each chip batch --------------
axB = fig.add_subplot(gs[0, 1])
ypos = np.arange(len(GENES))[::-1]
for yv, g in zip(ypos, GENES):
    xs = [per_chip[g][c] for c in chips]
    c = DARK if pooled[g] >= THRESH else WARM
    axB.plot([min(xs), max(xs)], [yv, yv], lw=1.3, color=c, alpha=0.35,
             zorder=1, solid_capstyle='round')
    axB.scatter(xs, [yv] * len(xs), s=26, facecolor='white', edgecolor=c,
                linewidth=1.1, zorder=3)
    axB.scatter([pooled[g]], [yv], s=74, color=c, edgecolor='white',
                linewidth=1.0, zorder=4)
    axB.text(102.5, yv, f'{min(xs):.0f}–{max(xs):.0f}', va='center',
             fontsize=7.2, color=c, weight='bold')
axB.axvline(THRESH, ls='--', lw=0.9, c='#888')
axB.text(THRESH, len(GENES) - 0.42, ' 85th percentile', fontsize=6.9,
         color='#666', style='italic', va='bottom')
axB.set_yticks(ypos)
axB.set_yticklabels(GENES, fontsize=8.8)
axB.set_xlim(62, 116)
axB.set_ylim(-0.75, len(GENES) - 0.30)
axB.set_xlabel('percentile, recomputed within each chip batch', fontsize=8.6)
axB.set_title('B. The same ranking inside each of the four batches\n'
              f'open circles, one batch each (n = '
              f'{", ".join(str(n_per_chip[c]) for c in chips)}); '
              'filled, all 28 pooled',
              fontsize=9.6, weight='bold', loc='left')
axB.tick_params(labelsize=8.0)
for s_ in ('top', 'right', 'left'):
    axB.spines[s_].set_visible(False)

out = FIG / 'Figure4_SarcUC.png'
plt.savefig(out, dpi=300, bbox_inches='tight')
plt.close()
print(f'Saved {out} ({out.stat().st_size:,} bytes)')
print(f'  universe {UNIVERSE:,} genes, {len(sarc)} tumors, {len(chips)} chip batches')
for g in GENES:
    xs = [per_chip[g][c] for c in chips]
    print(f'  {g:6s} pooled {pooled[g]:5.1f}   per batch '
          f'{min(xs):.1f}-{max(xs):.1f}   spread {max(xs)-min(xs):.1f}')
