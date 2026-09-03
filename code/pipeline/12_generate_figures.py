"""Generate all four manuscript figures.

Figure 1 — Pipeline schematic (fully matplotlib).
Figures 2 / 3 / 4 — Panels A and B (volcano, cross-cell consistency, KEGG
enrichment, subtype pie, subtype bars) are matplotlib reproducible
outputs from the deposited code. Panel C is rendered by imshow-ing the
deposited ChatGPT-generated cellular schematic PNGs (committed to
figures/chatgpt_schematics/ for provenance).
"""
import sys, json
from pathlib import Path

import paths
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg
from matplotlib.patches import FancyBboxPatch
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = paths.RESULTS
FIGURES = paths.FIGURES
SCHEMATICS = FIGURES / 'chatgpt_schematics'

plt.rcParams.update({
    'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
    'font.family': 'sans-serif',
    'axes.spines.top': False, 'axes.spines.right': False,
})


# =====================================================================
# Figure 1 — Pipeline schematic (compact aspect, Step 5 = G/E/P/L)
# =====================================================================
def generate_figure1():
    print("Generating Figure 1: pipeline schematic")
    fig, ax = plt.subplots(figsize=(11, 11.55))
    ax.set_xlim(0, 11); ax.set_ylim(-2.55, 9.0); ax.axis('off')

    ax.text(5.5, 8.75,
            'Figure 1. Public-Data Prioritization of Drug Hypotheses',
            ha='center', fontsize=13, weight='bold', color='#1a1a1a')
    ax.text(5.5, 8.45, 'Positive Controls and Rare-Cancer Prioritization',
            ha='center', fontsize=11.5, weight='bold', color='#1a1a1a')

    ax.add_patch(FancyBboxPatch((0.4, 7.75), 10.2, 0.55,
                                 boxstyle='round,pad=0.04',
                                 ec='#1a1a1a', fc='#1a3a5c', linewidth=1.2))
    ax.text(5.5, 8.13, '3 Positive Controls  +  4 Rare / Variant Discovery Cancers',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='white')
    ax.text(5.5, 7.88,
            'positive controls:  NEPC  |  MIBC  |  ccRCC          '
            'discovery:  RMC  |  PSCC  |  Sarcomatoid UC  |  SCBC',
            ha='center', va='center', fontsize=8.3, color='#e8e8e8',
            style='italic')
    ax.annotate('', xy=(5.5, 7.35), xytext=(5.5, 7.70),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#444'))

    ax.text(5.5, 7.22, 'Step 1.  Genomic evidence input',
            ha='center', fontsize=10, weight='bold', color='#1a1a1a')

    ax.add_patch(FancyBboxPatch((0.5, 5.65), 4.85, 1.45,
                                 boxstyle='round,pad=0.05',
                                 ec='#1f4e79', fc='#cfe2f3', linewidth=1.3))
    ax.text(2.925, 6.85, 'Step 1a — TCGA Pan-Cancer Atlas',
            ha='center', va='center', fontsize=9.2, weight='bold',
            color='#0b2e4f')
    ax.text(2.925, 6.55, 'Positive-control cohorts',
            ha='center', va='center', fontsize=8.2, style='italic',
            color='#1a1a1a')
    ax.text(2.925, 6.22,
            'PRAD  n = 494   (NEPC)\nBLCA  n = 411   (MIBC)\n'
            'KIRC  n = 512   (ccRCC)',
            ha='center', va='center', fontsize=8.0, color='#0b2e4f',
            family='monospace')
    ax.text(2.925, 5.78, '→ associations 1–16',
            ha='center', va='center', fontsize=8.0, weight='bold',
            color='#0b2e4f')

    ax.add_patch(FancyBboxPatch((5.65, 5.65), 4.85, 1.45,
                                 boxstyle='round,pad=0.05',
                                 ec='#2c6e49', fc='#d9ead3', linewidth=1.3))
    ax.text(8.075, 6.85, 'Step 1b — Published genomic series',
            ha='center', va='center', fontsize=9.2, weight='bold',
            color='#1d4d33')
    ax.text(8.075, 6.55, 'Rare-disease discovery cohorts',
            ha='center', va='center', fontsize=8.2, style='italic',
            color='#1a1a1a')
    ax.text(8.075, 6.22,
            'RMC: Msaouel 2020       PSCC: Chahoud 2021\n'
            'Sarc-UC: Guo 2019         SCBC: Chang 2018',
            ha='center', va='center', fontsize=7.7, color='#1d4d33',
            family='monospace')
    ax.text(8.075, 5.78, '→ associations 17–30',
            ha='center', va='center', fontsize=8.0, weight='bold',
            color='#1d4d33')

    ax.annotate('', xy=(5.5, 5.30), xytext=(2.925, 5.62),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#1f4e79'))
    ax.annotate('', xy=(5.5, 5.30), xytext=(8.075, 5.62),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#2c6e49'))

    unified_steps = [
        (4.62, 'Step 2',
         'GEO transcriptomic differential expression',
         '10 datasets  ·  limma / edgeR, a model matched to how each dataset was collected  ·  BH-FDR',
         '#fff2cc', '#806600'),
        (3.74, 'Step 3',
         '18 pre-specified druggable pathway / gene sets',
         'drug-class-first  ·  hypergeometric against each dataset\'s own measured-gene universe',
         '#fce5cd', '#a04a00'),
        (2.86, 'Step 4',
         'Drug–target curation',
         'Therapeutic Target Database  +  Open Targets (release 2026.03)',
         '#f4cccc', '#922b21'),
        (1.98, 'Step 5',
         '9-point Molecular Prioritization Score',
         'Genomic (0–3)  +  Transcriptomic (0–3)  +  '
         'KEGG (0–2)  +  Literature (0–1)',
         '#ead1dc', '#6c3483'),
        (1.10, 'Step 6',
         'PubMed search for prior proposals',
         'run after scoring; urologic-oncology literature only, '
         'per drug–cancer row',
         '#d0e0e3', '#1b5e6b'),
    ]
    box_x, box_w, box_h = 1.20, 8.60, 0.62
    for y, label, title, sub, fc, accent in unified_steps:
        ax.add_patch(FancyBboxPatch((box_x, y), box_w, box_h,
                                     boxstyle='round,pad=0.04',
                                     ec=accent, fc=fc, linewidth=1.1))
        ax.text(box_x + 0.30, y + box_h/2, label, ha='left', va='center',
                fontsize=9.5, weight='bold', color=accent)
        ax.text(5.50, y + 0.42, title, ha='center', va='center',
                fontsize=9.5, weight='bold', color='#1a1a1a')
        ax.text(5.50, y + 0.16, sub, ha='center', va='center',
                fontsize=7.8, color='#333')

    for head_y, tail_y in [(4.36, 4.62), (3.48, 3.74), (2.60, 2.86),
                            (1.72, 1.98)]:
        ax.annotate('', xy=(5.5, head_y), xytext=(5.5, tail_y),
                    arrowprops=dict(arrowstyle='->', lw=1.4, color='#444'))

    ax.annotate('', xy=(5.5, 0.92), xytext=(5.5, 1.08),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#1a1a1a'))

    ax.add_patch(FancyBboxPatch((0.40, 0.08), 10.20, 0.84,
                                 boxstyle='round,pad=0.05',
                                 ec='#7a4a00', fc='#fef5e7', linewidth=1.5))
    ax.text(5.50, 0.74,
            '30 Drug–Cancer Associations',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='#7a4a00')
    ax.text(2.20, 0.40, '18  previously proposed',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#0b2e4f')
    ax.text(2.20, 0.20, '(positive control)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#0b2e4f')
    ax.text(4.85, 0.40, '6  no prior proposal found',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#c00000')
    ax.text(4.85, 0.20, '(in the urologic-oncology literature)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#c00000')
    ax.text(7.30, 0.40, '5  partial precedents',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#6c3483')
    ax.text(7.30, 0.20, '(variant-specific extensions)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#6c3483')
    ax.text(9.50, 0.40, '1  biomarker observation',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#1d4d33')
    ax.text(9.50, 0.20, '(TROP2-low, not a drug hypothesis)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#1d4d33')

    # ---- Step 7: independent evidence for the no-prior-proposal column ----
    # Only the framework-novel column is carried forward, so the arrow leaves
    # from beneath that column rather than from the centre of the table box.
    ax.annotate('', xy=(4.85, -0.36), xytext=(4.85, 0.05),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#c00000'))
    ax.add_patch(FancyBboxPatch((1.20, -1.31), 8.60, 0.93,
                                 boxstyle='round,pad=0.04',
                                 ec='#1e8449', fc='#d4efdf', linewidth=1.1))
    ax.text(5.50, -0.62,
            'Step 7 \u2014 consistency checks; no source contributed to a score, '
            'and none changed the ranking',
            ha='center', va='center', fontsize=9.3, weight='bold',
            color='#1a1a1a')
    ax.text(5.50, -0.90,
            'Human Protein Atlas localisation + normal tissue   ·   '
            'DepMap CRISPR dependency (genotype-stratified)',
            ha='center', va='center', fontsize=7.5, color='#333')
    ax.text(5.50, -1.11,
            'PRISM Repurposing compound activity   ·   '
            'LINCS L1000 signature reversal',
            ha='center', va='center', fontsize=7.5, color='#333')

    ax.annotate('', xy=(5.5, -1.52), xytext=(5.5, -1.34),
                arrowprops=dict(arrowstyle='->', lw=1.8, color='#1a1a1a'))

    ax.add_patch(FancyBboxPatch((0.55, -2.42), 9.90, 0.94,
                                 boxstyle='round,pad=0.05',
                                 ec='#1a1a1a', fc='#1e8449', linewidth=1.4))
    ax.text(5.50, -1.72,
            'All 6 candidates reported \u2014 3 priority, 3 lower confidence',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='white')
    ax.text(5.50, -2.02,
            'priority: renal medullary carcinoma, CXCR1/CXCR2 blockade then '
            'anti-CEACAM1   \u00b7   ASCL1+ small-cell bladder, anti-CEACAM5\n'
            'lower confidence: NSD2 and ATR in sarcomatoid UC, SSTR2 in NEUROD1+ '
            'SCBC, each reported with its reservation',
            ha='center', va='center', fontsize=7.0, style='italic',
            color='#eafaf1')

    plt.savefig(FIGURES / 'Figure1_pipeline.png', bbox_inches='tight')
    plt.close()
    print(f"  Saved Figure1_pipeline.png "
          f"({(FIGURES/'Figure1_pipeline.png').stat().st_size:,} bytes)")


generate_figure1()


def panel_c_schematic(ax, png_path, title):
    """Embed a pre-rendered cellular schematic PNG as Panel C."""
    img = mpimg.imread(png_path)
    ax.imshow(img)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, fontsize=10.5, weight='bold', pad=8)


# =====================================================================
# Figure 2 — RMC
# =====================================================================
print("Generating Figure 2: RMC (panels A/B matplotlib + Panel C ChatGPT)")
xl_path = paths.RAW / 'GSE180999' / 'GSE180999_rnaseq_rmc_cell_lines_differential_expression.xlsx'
rmc2c = pd.read_excel(xl_path, sheet_name='RMC2C+SMARCB1')
rmc219 = pd.read_excel(xl_path, sheet_name='RMC219+SMARCB1')
rmc2c.columns = ['gene', 'l2fc_12h_RMC2C', 'q_12h_RMC2C',
                  'l2fc_48h_RMC2C', 'q_48h_RMC2C']
rmc219.columns = ['gene', 'l2fc_12h_RMC219', 'q_12h_RMC219',
                   'l2fc_48h_RMC219', 'q_48h_RMC219']
de = pd.merge(rmc2c, rmc219, on='gene').dropna(
    subset=['l2fc_48h_RMC2C', 'q_48h_RMC2C', 'l2fc_48h_RMC219', 'q_48h_RMC219'])
# Figures 2-5 below are SUPERSEDED (v29): they are regenerated by
# 40/42/46_*_v29.py from the refit. Their v25 inputs are not part of the
# current deposit, so skip rather than fail when they are absent.
if not (RESULTS / 'RMC_up_in_null_state.csv').exists():
    print('  superseded v25 panels skipped (inputs not in the current deposit)')
    raise SystemExit(0)
rmc_up = pd.read_csv(RESULTS / 'RMC_up_in_null_state.csv')
top_genes = rmc_up['gene'].tolist()

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.30],
                       hspace=0.42, wspace=0.45,
                       left=0.08, right=0.97, top=0.94, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

# Volcano oriented so that POSITIVE log₂FC = upregulated in the SMARCB1-null
# (RMC) disease state. Achieved by negating the rescue-vs-null log₂FC
# stored in the deposited table so the contrast displayed is
# SMARCB1-null vs SMARCB1-rescue (i.e., disease state vs control).
de_l2fc_disease = -de['l2fc_48h_RMC2C']
neg_log_q = -np.log10(de['q_48h_RMC2C'].clip(lower=1e-300))
axA.scatter(de_l2fc_disease, neg_log_q, s=4, c='lightgrey', alpha=0.5)
highlight = de[de['gene'].isin(top_genes)]
axA.scatter(-highlight['l2fc_48h_RMC2C'],
            -np.log10(highlight['q_48h_RMC2C'].clip(lower=1e-300)),
            s=30, c='red', edgecolor='black', linewidth=0.5, zorder=5)
rmc_label_offsets = {          # explicit offsets prevent label/point collision
    'IL8':     (0.30,  12),
    'CXCL1':   (0.35,  14),
    'CEACAM1': (-1.55, 22),
    'CXCL2':   (0.35,  26),
    'HBEGF':   (-1.75, 34),
}
for _, r in highlight.iterrows():
    g = r['gene']
    x = -r['l2fc_48h_RMC2C']  # flip sign for disease-state orientation
    y = -np.log10(max(r['q_48h_RMC2C'], 1e-300))
    if g in rmc_label_offsets:
        dx, dy = rmc_label_offsets[g]
        axA.annotate(g, (x, y), xytext=(x + dx, y + dy), fontsize=7,
                     fontweight='bold', color='darkred',
                     arrowprops=dict(arrowstyle='-', color='darkred',
                                     lw=0.6, alpha=0.6))
axA.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.set_xlabel('log₂FC (SMARCB1-null vs SMARCB1-rescue, RMC-2C cells)\n'
               '← DOWN in RMC         UP in RMC →')
axA.set_ylabel('−log₁₀(adj. p-value)   [clipped at 300]')
axA.set_title('A. Volcano plot — RMC-2C cell line\n'
              'GSE180999 (n=9; SMARCB1-null vs rescue)',
              fontsize=9.5, pad=8)
axA.set_xlim(-9, 3)
axA.set_ylim(-10, 335)
axA.text(0.02, 0.985,
         'Cell-line rescue contrast; q-values clipped at 1e-300.' + chr(10) +
         'Effect direction and magnitude, not p, drive prioritization.',
         transform=axA.transAxes, fontsize=6, style='italic',
         color='#555', va='top')

top_df = rmc_up.sort_values('mean_l2fc_48h')
y_pos = np.arange(len(top_df))
axB.barh(y_pos - 0.2, -top_df['l2fc_48h_RMC2C'], height=0.4,
         label='RMC-2C', color='steelblue')
axB.barh(y_pos + 0.2, -top_df['l2fc_48h_RMC219'], height=0.4,
         label='RMC219', color='lightcoral')
axB.set_yticks(y_pos)
axB.set_yticklabels(top_df['gene'], fontsize=8)
axB.set_xlabel('log₂FC UP in SMARCB1-null state\n(positive = elevated in RMC)')
axB.set_title('B. Cross-cell-line consistency of\nSMARCB1-null UP genes',
              fontsize=9.5, pad=8)
axB.legend(loc='lower right', frameon=True)
axB.axvline(1, color='red', linestyle='--', lw=0.8)
axB.grid(axis='x', alpha=0.3)

panel_c_schematic(axC, SCHEMATICS / 'Figure2_PanelC_RMC.png',
                  'C. Proposed cellular mechanism — RMC chemokine axis '
                  'and framework-novel drug-class candidates')

plt.suptitle('Figure 2. Renal Medullary Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.985)
plt.savefig(FIGURES / 'Figure2_RMC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure2_RMC.png ({(FIGURES/'Figure2_RMC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 3 — Sarc-UC
# =====================================================================
print("\nGenerating Figure 3: Sarc-UC (panels A/B matplotlib + Panel C ChatGPT)")
sarc_de = pd.read_csv(RESULTS / 'SarcomatoidUC_DE_full.csv')

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.30],
                       hspace=0.45, wspace=0.60,
                       left=0.08, right=0.97, top=0.93, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

sarc_de_dedup = (sarc_de.sort_values('qvalue')
                       .drop_duplicates(subset='gene', keep='first'))
axA.scatter(sarc_de_dedup['log2fc'],
            -np.log10(sarc_de_dedup['qvalue'].clip(lower=1e-30)),
            s=3, c='lightgrey', alpha=0.4)
novel_targets = ['WHSC1', 'ATRIP', 'UHRF1', 'G6PD', 'PHC2']
neg_target = ['TACSTD2']
label_offsets = {
    'UHRF1':   (0.35, 1.0),
    'WHSC1':   (-0.75, 1.5),
    'PHC2':    (0.30, -0.5),
    'ATRIP':   (-0.75, -1.5),
    'G6PD':    (0.30, -0.8),
    'TACSTD2': (0.20, 0.5),
}
for tgt, col in [(novel_targets, 'red'), (neg_target, 'blue')]:
    sub = sarc_de_dedup[sarc_de_dedup['gene'].isin(tgt)]
    axA.scatter(sub['log2fc'], -np.log10(sub['qvalue'].clip(lower=1e-30)),
                s=60, c=col, edgecolor='black', linewidth=0.5, zorder=10)
    for _, r in sub.iterrows():
        x = r['log2fc']
        y = -np.log10(max(r['qvalue'], 1e-30))
        dx, dy = label_offsets.get(r['gene'], (0.2, 0.5))
        axA.annotate(r['gene'], (x, y),
                     xytext=(x + dx, y + dy),
                     fontsize=8, fontweight='bold', color=col,
                     arrowprops=dict(arrowstyle='-', color=col,
                                     lw=0.6, alpha=0.6))
axA.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.set_xlabel('log₂FC (Sarcomatoid UC vs conventional UC)\n← DOWN in sarcomatoid     UP in sarcomatoid →')
axA.set_ylabel('−log₁₀(adj. p-value)   [clipped at 30]')
axA.set_xlim(-3.0, 2.5)
axA.set_title('A. Volcano — Sarcomatoid UC (n=28) vs conventional UC (n=84)\n'
              'GSE128192; novel targets red, negative biomarker blue',
              fontsize=9.5, pad=8)

enr_all = json.load(open(RESULTS / 'kegg_enrichment_all_diseases.json'))
sarc_enr = enr_all['SarcUC']
def _bh(pvals):
    'Benjamini-Hochberg q-values across the 18 pre-specified gene sets.'
    pv = np.asarray(pvals, dtype=float)
    n_t = pv.size
    order = np.argsort(pv)
    q = pv[order] * n_t / np.arange(1, n_t + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n_t)
    out[order] = np.clip(q, 0, 1)
    return out

_all_names = list(sarc_enr.keys())
_bh_map = dict(zip(_all_names,
                   _bh([sarc_enr[nm]['pvalue'] for nm in _all_names])))

top_paths = sorted([(p, r['pvalue'], r['overlap']) for p, r in sarc_enr.items()
                    if r['overlap'] > 0], key=lambda x: x[1])[:8]
def prettify(name: str) -> str:
    s = name.replace('_', ' ')
    s = s.replace('PDL1 PD1 checkpoint', 'PD-L1 / PD-1 checkpoint')
    s = s.replace('PI3K AKT signaling', 'PI3K / AKT signaling')
    return s

top_paths_sorted = sorted(top_paths, key=lambda x: x[1], reverse=True)
names_pretty = [prettify(p) for p, _, _ in top_paths_sorted]
pvals = [-np.log10(p) for _, p, _ in top_paths_sorted]
overlaps = [o for _, _, o in top_paths_sorted]
colors = ['#922b21' if v > 1 else '#4a78b3' for v in pvals]
y_b = np.arange(len(names_pretty))
axB.barh(y_b, pvals, color=colors, edgecolor='black', linewidth=0.4)
axB.set_yticks(y_b)
axB.set_yticklabels(names_pretty, fontsize=8)
axB.set_xlabel('−log₁₀(p-value), hypergeometric')
axB.set_title('B. KEGG pathway enrichment — Sarcomatoid UC upregulated genes',
              fontsize=9.5, pad=8)
axB.axvline(-np.log10(0.10), color='red', linestyle='--', lw=0.8, alpha=0.5)
xmax = max(pvals) * 1.15
axB.set_xlim(0, xmax)
qs_bh = [_bh_map[nm] for nm, _, _ in top_paths_sorted]
for i, (v, o, q_bh) in enumerate(zip(pvals, overlaps, qs_bh)):
    star = '  *' if q_bh < 0.10 else ''
    axB.text(v + xmax * 0.02, i, f'k = {o}{star}', fontsize=7.5,
             va='center', ha='left', color='#333')
axB.text(0.98, 0.03,
         'bars = nominal hypergeometric p (scoring basis)' + chr(10) +
         '* = also survives Benjamini-Hochberg FDR q < 0.10',
         transform=axB.transAxes, fontsize=6.5, style='italic',
         ha='right', va='bottom', color='#555')
axB.grid(axis='x', alpha=0.3)

panel_c_schematic(axC, SCHEMATICS / 'Figure3_PanelC_SarcUC.png',
                  'C. Proposed cellular mechanism — Sarcomatoid UC framework-'
                  'novel targets + TROP2-low negative biomarker')

plt.suptitle('Figure 3. Sarcomatoid Urothelial Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'FigureS1_SarcUC.png', bbox_inches='tight')
plt.close()
print(f"  Saved FigureS1_SarcUC.png ({(FIGURES/'FigureS1_SarcUC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 4 — SCBC
# =====================================================================
print("\nGenerating Figure 4: SCBC (panels A/B matplotlib + Panel C ChatGPT)")
scbc_subtypes = pd.read_csv(RESULTS / 'SCBC_subtype_calls.csv')
ascl1_df = pd.read_csv(RESULTS / 'SCBC_up_in_ASCL1.csv').head(10)
neur_full = pd.read_csv(RESULTS / 'SCBC_up_in_NEUROD1.csv')
# SSTR2 is the nominated theranostic target for this subtype. It is
# significant but ranks below the top genes by fold change, so it is shown
# explicitly alongside the top 7 rather than being silently omitted.
neur_df = pd.concat([neur_full.head(7),
                     neur_full[neur_full['gene'] == 'SSTR2']],
                    ignore_index=True)
assert 'SSTR2' in set(neur_df['gene']), 'SSTR2 must appear in Figure 4B'

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.30],
                       hspace=0.45, wspace=0.45,
                       left=0.08, right=0.97, top=0.93, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

counts = scbc_subtypes['subtype'].value_counts()
# Colour keyed by subtype NAME, not by count order, so POU2F3 is the same colour
# in the pie, the bar panel and the Panel C schematic.
SUBTYPE_COLOR = {'ASCL1': '#3498db', 'NEUROD1': '#9b59b6',
                 'POU2F3': '#e67e22', 'YAP1': '#27ae60'}
colors_pie = [SUBTYPE_COLOR.get(s, '#95a5a6') for s in counts.index]
_pie_n = list(counts.values)          # label from the actual subtype counts,
_pie_i = iter(range(len(_pie_n)))     # never from the rounded percentage


def _pie_label(pct):
    k = _pie_n[next(_pie_i)]
    return 'n=' + str(k) + chr(10) + '(' + format(pct, '.0f') + '%)'


assert sum(_pie_n) == 44, 'subtype calls must sum to 44, got ' + str(sum(_pie_n))
axA.pie(counts.values, labels=counts.index,
        colors=colors_pie,
        autopct=_pie_label,
        startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
axA.set_title('A. SCBC subtype distribution (n=44)' + chr(10) +
              'classified by maximum lineage-TF expression — GSE269750',
              fontsize=9.5, pad=8)

# ---- Panel B: three lineage subtypes, each with its nominated target ---------
# The nominated target is forced into its block where it does not reach the top
# by fold change (SSTR2 ranks 12th, PTGS1 14th); CEACAM5 ranks 2nd and needs no
# special handling. Without this the panel would claim to highlight targets it
# never actually plots.
pou_full = pd.read_csv(RESULTS / 'SCBC_up_in_POU2F3.csv')

N_TOP = 5
BLOCKS = [
    ('ASCL1+', ascl1_df, 'CEACAM5', SUBTYPE_COLOR['ASCL1']),
    ('NEUROD1+', neur_full, 'SSTR2', SUBTYPE_COLOR['NEUROD1']),
    ('POU2F3+', pou_full, 'PTGS1', SUBTYPE_COLOR['POU2F3']),
]
HEADLINE = '#922b21'

frames = []
for label, df_all, target, color in BLOCKS:
    df_all = df_all.sort_values('log2fc', ascending=False)
    top = df_all.head(N_TOP)
    if target not in set(top['gene']):
        extra = df_all[df_all['gene'] == target]
        assert not extra.empty, label + ' is missing its nominated target ' + target
        top = pd.concat([top, extra], ignore_index=True)
    top = top.copy()
    top['block'] = label
    top['color'] = [HEADLINE if g == target else color for g in top['gene']]
    frames.append(top)

gap = 1.5
y_cursor = 0.5
block_y, divider_y = [], []
for frame in reversed(frames):                 # bottom block drawn first
    n = len(frame)
    ys = np.arange(n)[::-1] + y_cursor
    block_y.append((frame, ys))
    y_cursor += n + gap
    divider_y.append(y_cursor - gap / 2)
block_y.reverse()
divider_y = divider_y[:-1]

for frame, ys in block_y:
    for i, (_, r) in enumerate(frame.iterrows()):
        axB.barh(ys[i], r['log2fc'], color=r['color'], edgecolor='black',
                 linewidth=0.4, height=0.7)

ticks, labels_ = [], []
for frame, ys in block_y:
    ticks.extend(list(ys))
    labels_.extend(list(frame['gene']))
axB.set_yticks(ticks)
axB.set_yticklabels(labels_, fontsize=7.5)
axB.set_xlabel('log₂FC (subtype vs other subtypes)')
axB.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axB.grid(axis='x', alpha=0.3)
for dy in divider_y:
    axB.axhline(dy, color='#888', lw=0.6, alpha=0.5)

for (frame, ys), (label, _, target, color) in zip(block_y, BLOCKS):
    axB.text(0.985, ys.max() + 0.55, label + '  ·  ' + target + ' (red)',
             ha='right', va='center', transform=axB.get_yaxis_transform(),
             fontsize=7.5, weight='bold', color=color,
             bbox=dict(boxstyle='round,pad=0.25', facecolor='white',
                       edgecolor=color, linewidth=0.8, alpha=0.9))

axB.set_ylim(-0.6, y_cursor - gap + 0.6)
axB.set_title('B. Headline subtype-stratified upregulated genes' + chr(10) +
              'nominated targets CEACAM5, SSTR2 and PTGS1 in dark red',
              fontsize=9.5, pad=8)

panel_c_schematic(axC, SCHEMATICS / 'Figure4_PanelC_SCBC.png',
                  'C. Proposed cellular mechanism — Lineage-stratified SCBC '
                  'framework-novel cell-surface targets')

plt.suptitle('Figure 4. Small-Cell Bladder Cancer — Lineage-Stratified Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure3_SCBC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure3_SCBC.png ({(FIGURES/'Figure3_SCBC.png').stat().st_size:,} bytes)")

print("\nAll three figures regenerated with ChatGPT cellular schematics.")
