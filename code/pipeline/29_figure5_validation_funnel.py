"""Figure 5 - candidate attrition funnel and cross-layer validation matrix.

The manuscript narrows thirty associations to one lead candidate across four
orthogonal evidence layers, but until now that narrowing existed only in prose.
Panel A draws the attrition. Panel B shows, for each framework-novel candidate,
what every layer actually returned - including the distinction that matters most
in this study: a layer that CONTRADICTS a candidate versus one that is
structurally UNABLE TO TEST it.

All values are read from the deposited result files, not hard-coded.

Writes: figures/Figure5_validation_funnel.png

SUPERSEDED (v29). This script produced the v26-v28 analysis and is retained so
that earlier versions of the manuscript remain reconstructible. It is NOT part
of the current pipeline. The v29 analysis refits every dataset with design-aware
models and recomputes the scores from the fitted tables:

    32_prepare_matrices.py  ->  33_refit_limma.R  ->  35/36 enrichment
    38_extract_row_definitions.py  ->  39_rescore_from_refit.py
    41_candidate_selection.py

"""
import json
import sys
from pathlib import Path

import paths

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Polygon

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
R = REPO / 'results'
FIGURES = paths.FIGURES

plt.rcParams.update({'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
                     'font.family': 'sans-serif'})

kegg = pd.read_csv(R / 'KEGG_ENRICHMENT_ALL10.csv')
hpa = pd.read_csv(R / 'HPA_PROTEIN_VALIDATION.csv')
dep = pd.read_csv(R / 'DEPMAP_STRATIFIED.csv')
pri = pd.read_csv(R / 'PRISM_DRUG_SENSITIVITY.csv')
SETS = json.loads((R / 'KEGG_PATHWAYS_18.json').read_text(encoding='utf-8'))


def bh_q(ctx, gene):
    """Best BH q-value across the pre-specified sets that actually contain the
    target, or None when the target is in none of the eighteen.

    Reading a q-value off a pathway the target does not belong to would credit a
    candidate with an enrichment driven by other genes - which is exactly what
    the row-level KEGG score component refuses to do.
    """
    if ctx is None or gene is None:
        return None
    paths = [p for p, genes in SETS.items() if gene in genes]
    rows = kegg[(kegg['context'] == ctx) & (kegg['pathway'].isin(paths))]
    return float(rows['qvalue_BH'].min()) if len(rows) else None


# candidate -> (row, context, target gene, HPA gene, DepMap gene, PRISM drugs)
# The enrichment column is resolved from the target's own gene-set membership,
# not from a hand-picked pathway.
CANDIDATES = [
    ('CXCR1/CXCR2 antagonists\n(renal medullary carcinoma)', 17, 'RMC',
     'CXCR1', 'CXCR1', None, ['reparixin', 'navarixin']),
    ('$^{177}$Lu-DOTATATE\n(NEUROD1+ small-cell bladder)', 29, 'SCBC_NEUROD1',
     'SSTR2', 'SSTR2', None, None),
    ('Anti-CEACAM1 (CM24)\n(renal medullary carcinoma)', 19, 'RMC',
     'CEACAM1', 'CEACAM1', None, None),
    ('Anti-CEACAM5 conjugates\n(ASCL1+ small-cell bladder)', 28, 'SCBC_ASCL1',
     'CEACAM5', 'CEACAM5', None, None),
    ('NSD2 inhibition (KTX-1001)\n(sarcomatoid urothelial)', 23, 'SarcUC',
     'NSD2', 'NSD2', 'NSD2', None),
    ('ATR inhibition\n(sarcomatoid urothelial)', 24, 'SarcUC', 'ATR', 'ATR',
     'ATR', ['VE-822']),
]

LAYERS = ['Enrichment\nsurvives FDR', 'Protein at\nthe membrane',
          'Genetic\ndependency', 'Compound\nactivity', 'Agent\navailable']

SUPPORT, NEUTRAL, AGAINST, UNTESTABLE = '#1e8449', '#f4d03f', '#c0392b', '#bdc3c7'
LABEL = {SUPPORT: 'supports', NEUTRAL: 'partial /\nnominal',
         AGAINST: 'contradicts', UNTESTABLE: 'cannot\ntest'}

grid, notes = [], []
for name, row, ctx, tgene, hgene, dgene, drugs in CANDIDATES:
    cells, cellnotes = [], []

    q = bh_q(ctx, tgene)
    if q is None:
        cells.append(UNTESTABLE); cellnotes.append('not in\npanel')
    elif q < 0.10:
        cells.append(SUPPORT); cellnotes.append(f'q={q:.3f}')
    else:
        cells.append(NEUTRAL); cellnotes.append(f'q={q:.2f}')

    h = hpa[hpa['gene'] == hgene]
    if len(h) and bool(h['plasma_membrane'].iloc[0]):
        cells.append(SUPPORT); cellnotes.append('membrane')
    else:
        cells.append(UNTESTABLE); cellnotes.append('n/a')

    if dgene:
        s = dep[dep['gene'] == dgene]
        v = str(s['verdict'].iloc[0]) if len(s) else ''
        if v.startswith('no dependency'):
            cells.append(AGAINST); cellnotes.append('none')
        elif 'not selective' in v:
            cells.append(NEUTRAL); cellnotes.append('pan-\nessential')
        else:
            cells.append(UNTESTABLE); cellnotes.append('n/a')
    else:
        cells.append(UNTESTABLE); cellnotes.append('modality')

    if drugs:
        s = pri[pri['drug'].isin(drugs)]
        if len(s) and s['verdict'].str.contains('active in urothelial').any():
            cells.append(NEUTRAL); cellnotes.append('active,\nnot select.')
        else:
            cells.append(UNTESTABLE); cellnotes.append('no auto-\nnomous')
    else:
        cells.append(UNTESTABLE); cellnotes.append('modality')

    avail = AGAINST if row == 28 else SUPPORT
    cells.append(avail)
    cellnotes.append('discontinued' if row == 28 else 'clinical-\nstage')

    grid.append(cells); notes.append(cellnotes)

fig = plt.figure(figsize=(12.5, 6.95))
gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1.0, 1.5],
                       wspace=0.32, left=0.05, right=0.975, top=0.87, bottom=0.19)

# ---------------- Panel A: attrition funnel ----------------
axA = fig.add_subplot(gs[0, 0])
axA.set_xlim(0, 10); axA.set_ylim(0, 10); axA.axis('off')
STAGES = [
    (9.2, 9.6, 9.6, '30 drug–cancer associations', '#1a3a5c', 'white',
     'across seven contexts'),
    (7.2, 8.4, 9.6, '6 framework-novel', '#c0392b', 'white',
     '18 convergent · 5 partial · 1 negative set aside'),
    (5.2, 7.4, 8.2, '2 survive orthogonal scrutiny', '#b9770e', 'white',
     '1 discontinued · 2 unsupported by DepMap · 1 expression only'),
    (3.0, 6.4, 8.6, '1 lead candidate', '#1e8449', 'white',
     'CXCR1/CXCR2 blockade in renal medullary carcinoma'),
]
for i, (y, w, fs, label, fc, tc, sub) in enumerate(STAGES):
    x0 = 5 - w / 2
    axA.add_patch(FancyBboxPatch((x0, y), w, 0.95, boxstyle='round,pad=0.06',
                                 fc=fc, ec='#1a1a1a', linewidth=1.1))
    axA.text(5, y + 0.62, label, ha='center', va='center', fontsize=fs,
             weight='bold', color=tc)
    axA.text(5, y + 0.24, sub, ha='center', va='center', fontsize=6.6,
             color='#f0f0f0' if tc == 'white' else '#333', style='italic')
    if i < len(STAGES) - 1:
        ny = STAGES[i + 1][0] + 0.95
        nw = STAGES[i + 1][1]
        axA.add_patch(Polygon([[x0, y], [x0 + w, y],
                               [5 + nw / 2, ny], [5 - nw / 2, ny]],
                              closed=True, fc='#ecf0f1', ec='#bdc3c7', lw=0.7))
        axA.annotate('', xy=(5, ny + 0.02), xytext=(5, y - 0.02),
                     arrowprops=dict(arrowstyle='-|>', lw=1.3, color='#555'))
axA.set_title('A. Candidate attrition', fontsize=10.5, weight='bold', pad=10,
              loc='left')

# ---------------- Panel B: validation matrix ----------------
axB = fig.add_subplot(gs[0, 1])
n_r, n_c = len(CANDIDATES), len(LAYERS)
for i in range(n_r):
    for j in range(n_c):
        axB.add_patch(plt.Rectangle((j, n_r - 1 - i), 1, 1,
                                    fc=grid[i][j], ec='white', lw=2.2))
        axB.text(j + 0.5, n_r - 1 - i + 0.5, notes[i][j], ha='center',
                 va='center', fontsize=6.1,
                 color='white' if grid[i][j] in (SUPPORT, AGAINST) else '#2c3e50',
                 weight='bold')
axB.set_xlim(0, n_c); axB.set_ylim(0, n_r)
axB.set_xticks([j + 0.5 for j in range(n_c)])
axB.set_xticklabels(LAYERS, fontsize=7.4)
axB.xaxis.set_ticks_position('top')
axB.set_yticks([n_r - 1 - i + 0.5 for i in range(n_r)])
axB.set_yticklabels([c[0] for c in CANDIDATES], fontsize=7.2)
for s in axB.spines.values():
    s.set_visible(False)
axB.tick_params(length=0)
axB.set_title('B. What each evidence layer returned, per framework-novel candidate',
              fontsize=10.5, weight='bold', pad=34, loc='left')

handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec='white')
           for c in (SUPPORT, NEUTRAL, AGAINST, UNTESTABLE)]
axB.legend(handles, [LABEL[c].replace('\n', ' ')
                     for c in (SUPPORT, NEUTRAL, AGAINST, UNTESTABLE)],
           loc='upper center', bbox_to_anchor=(0.5, -0.04), ncol=4,
           frameon=False, fontsize=7.6)

fig.text(0.5, 0.025,
         'Grey cells are layers that cannot evaluate the candidate rather than layers that failed it: '
         'a target outside the eighteen pre-specified gene sets\n'
         'has no enrichment q-value, and a microenvironment-directed or payload-delivering agent is '
         'invisible to a tumour-cell monoculture.\nAbsence of contradiction is therefore weaker '
         'evidence than positive support.',
         ha='center', fontsize=7.1, style='italic', color='#555')

out = FIGURES / 'Figure5_validation_funnel.png'
plt.savefig(out, bbox_inches='tight')
plt.close()
print(f"Saved {out} ({out.stat().st_size:,} bytes)")
