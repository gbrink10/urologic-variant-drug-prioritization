"""Figure 2. How each association was nominated, by route and by cancer.

Two routes produced the association table, and the evidence that drove each one
is a different quantity, so each gets its own axis rather than being forced onto
a shared one.

  A  The Cancer Genome Atlas route. The three positive controls have a genomic
     cohort, so genes were ranked by how often they are altered.
  B  The Gene Expression Omnibus route. The four rare cancers have no such
     cohort, so genes were ranked by differential expression.
  C  The same route where no disease-versus-comparator contrast is available,
     so genes are ranked by abundance within the tumors instead. This is the
     sarcomatoid series, whose histology is aliased with array chip.

Fill marks whether the gene belongs to one of the eighteen pre-specified
druggable gene sets. Panel membership scores a candidate; it never gated one,
and the open markers are the genes that entered without it.

Writes: figures/FigureS2_selection_routes.png
"""
import json
import re
import sys
from pathlib import Path

import paths
import lib_symbols

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
FIG = paths.FIGURES

defs = pd.read_csv(REPO / 'data' / 'master_row_definitions.csv')
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
d = defs.merge(prov[['N', 'arm', 'E_basis', 'refit_log2FC']], on='N')

panel = set()
for v in json.loads((REPO / 'results' / 'KEGG_PATHWAYS_18.json')
                    .read_text(encoding='utf-8')).values():
    panel |= set(lib_symbols.normalize(pd.Series(v)).values)
d['in_panel'] = d['scoring_gene'].astype(str).str.upper().isin(panel)


def pct_of(basis):
    m = re.search(r'([\d.]+)th percentile', str(basis))
    return float(m.group(1)) if m else None


d['pct'] = d['E_basis'].map(pct_of)

# panel A is the TCGA-anchored rows, B and C split the GEO-anchored rows by
# whether a disease contrast was available
A = d[d['N'] <= 16].copy()
G = d[d['N'] > 16].copy()
B = G[G['pct'].isna()].copy()
C = G[G['pct'].notna()].copy()

NAVY, RED, GREY = '#1a3a5c', '#a93226', '#7f8c8d'
BANDS = {3: '>30%', 2: '15–30%', 1: '5–15%', 0: '<5%'}

fig = plt.figure(figsize=(15.4, 7.4))
gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 0.72], wspace=0.55)


def draw(ax, sub, value, color, xlabel, title, subtitle, xlim=None,
         band_ticks=False):
    """One horizontal lollipop panel.

    Each cancer gets a bold in-axes header above its genes, rather than a
    rotated label beside them: several cancers contribute a single gene, and
    rotated labels collide when the group is one row tall.
    """
    sub = sub.sort_values(['Context', value], ascending=[True, False])
    ypos, labels, headers = [], [], []
    y = 0.0
    for ctx, grp in sub.groupby('Context', sort=False):
        headers.append((y, ctx))
        y -= 0.85
        for _, r in grp.iterrows():
            v = float(r[value])
            ax.plot([0, v], [y, y], color=color, lw=1.5, alpha=0.55,
                    zorder=1, solid_capstyle='round')
            ax.scatter([v], [y], s=66, zorder=3, color=color,
                       edgecolor=color, linewidth=1.5,
                       facecolor=color if r['in_panel'] else 'white')
            ypos.append(y)
            labels.append(r['scoring_gene'])
            y -= 1.0
        y -= 0.5
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=8.8)
    ax.set_xlabel(xlabel, fontsize=8.8)
    ax.set_title(title, fontsize=10.4, weight='bold', loc='left', pad=15)
    ax.text(0, 1.018, subtitle, transform=ax.transAxes, fontsize=8.1,
            style='italic', color='#566573')
    if band_ticks:
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels([BANDS[i] for i in (0, 1, 2, 3)], fontsize=8.2)
        ax.set_xlim(-0.28, 3.5)
    elif xlim:
        ax.set_xlim(*xlim)
    ax.set_ylim(y + 0.4, 1.0)
    for s_ in ('top', 'right'):
        ax.spines[s_].set_visible(False)
    ax.grid(axis='x', color='#eaecee', lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    # cancer headers, drawn after the limits are fixed so they sit flush left
    x0 = ax.get_xlim()[0]
    for yy, ctx in headers:
        ax.text(x0, yy, ctx, ha='left', va='center', fontsize=8.6,
                weight='bold', color='#2c3e50')
    return ax


axA = fig.add_subplot(gs[0, 0])
draw(axA, A, 'genomic_score_curated', NAVY,
     'alteration frequency in the source cohort',
     'A. The Cancer Genome Atlas route',
     'three positive controls  ·  ranked by how often the gene is altered',
     band_ticks=True)

axB = fig.add_subplot(gs[0, 1])
B['lfc'] = B['refit_log2FC'].astype(float)
draw(axB, B, 'lfc', RED, 'log$_2$ fold change in the disease state',
     'B. The Gene Expression Omnibus route',
     'four rare cancers  ·  ranked by differential expression',
     xlim=(min(-2.6, B['lfc'].min() - 0.6), B['lfc'].max() + 1.5))
axB.axvline(0, color='#34495e', lw=0.9)

axC = fig.add_subplot(gs[0, 2])
draw(axC, C, 'pct', GREY, 'percentile of measured transcripts',
     'C. Same route, no contrast available',
     'ranked by abundance within the tumors', xlim=(0, 108))
for x in (67, 85, 95):
    axC.axvline(x, color='#bdc3c7', lw=0.8, ls=':')

leg = [Line2D([0], [0], marker='o', color='w', markerfacecolor='#34495e',
              markeredgecolor='#34495e', markersize=8,
              label='gene is in one of the 18 pre-specified sets'),
       Line2D([0], [0], marker='o', color='w', markerfacecolor='white',
              markeredgecolor='#34495e', markeredgewidth=1.5, markersize=8,
              label='gene is not — panel membership scores a candidate, '
                    'it never gated one')]
fig.legend(handles=leg, loc='lower center', ncol=2, frameon=False,
           fontsize=8.6, bbox_to_anchor=(0.5, -0.012))

fig.text(0.5, -0.055,
         'Every gene shown met the same two requirements: it stood out in its '
         'own cancer, and an agent against it could be evaluated clinically. '
         'The routes differ only in what "stood out" could mean, which '
         'depends on\nwhether that cancer has a genomic cohort. TROP2 in '
         'panel B is negative because it was nominated as a loss marker. '
         'Panel C is the sarcomatoid series, whose histology is aliased with '
         'array chip, so no contrast is interpretable.',
         ha='center', fontsize=8.0, style='italic', color='#5d6d7e')

out = FIG / 'FigureS2_selection_routes.png'
plt.savefig(out, dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print(f"Saved {out.name} ({out.stat().st_size:,} bytes)")
print(f"  A: {len(A)} TCGA-anchored   B: {len(B)} GEO contrast   "
      f"C: {len(C)} GEO abundance   total {len(A) + len(B) + len(C)}")
print(f"  in a pre-specified set: {int(d['in_panel'].sum())} of {len(d)}")
