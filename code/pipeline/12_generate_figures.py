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
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg
from matplotlib.patches import FancyBboxPatch
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")
FIGURES = Path(r"C:\Users\garre\framework_expansion\figures")
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
    fig, ax = plt.subplots(figsize=(11, 9.0))
    ax.set_xlim(0, 11); ax.set_ylim(0, 9.0); ax.axis('off')

    ax.text(5.5, 8.75,
            'Figure 1. Unified Public-Data Pipeline for Drug Repurposing',
            ha='center', fontsize=13, weight='bold', color='#1a1a1a')
    ax.text(5.5, 8.45, 'Across Seven Aggressive Urologic Cancer Contexts',
            ha='center', fontsize=11.5, weight='bold', color='#1a1a1a')

    ax.add_patch(FancyBboxPatch((0.4, 7.75), 10.2, 0.55,
                                 boxstyle='round,pad=0.04',
                                 ec='#1a1a1a', fc='#1a3a5c', linewidth=1.2))
    ax.text(5.5, 8.13, '7 Aggressive Urologic Cancer Contexts',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='white')
    ax.text(5.5, 7.88,
            'NEPC   |   MIBC   |   ccRCC   |   RMC   |   PSCC   |   '
            'Sarcomatoid UC   |   SCBC',
            ha='center', va='center', fontsize=8.5, color='#e8e8e8',
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
    ax.text(2.925, 6.55, 'Source-disease cohorts',
            ha='center', va='center', fontsize=8.2, style='italic',
            color='#1a1a1a')
    ax.text(2.925, 6.22,
            'PRAD  n = 494   (NEPC)\nBLCA  n = 411   (MIBC)\n'
            'KIRC  n = 512   (ccRCC)',
            ha='center', va='center', fontsize=8.0, color='#0b2e4f',
            family='monospace')
    ax.text(2.925, 5.78, '→ Master Table 1 rows 1–16',
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
            'RMC: Msaouel 2020       PSCC: Chahoud 2022\n'
            'Sarc-UC: Guo 2019         SCBC: Chang 2018',
            ha='center', va='center', fontsize=7.7, color='#1d4d33',
            family='monospace')
    ax.text(8.075, 5.78, '→ Master Table 1 rows 17–30',
            ha='center', va='center', fontsize=8.0, weight='bold',
            color='#1d4d33')

    ax.annotate('', xy=(5.5, 5.30), xytext=(2.925, 5.62),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#1f4e79'))
    ax.annotate('', xy=(5.5, 5.30), xytext=(8.075, 5.62),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#2c6e49'))

    unified_steps = [
        (4.62, 'Step 2',
         'GEO transcriptomic differential expression',
         '10 datasets across all 7 contexts  ·  Welch t-test, BH-FDR',
         '#fff2cc', '#806600'),
        (3.74, 'Step 3',
         '18 pre-specified druggable pathway / gene sets',
         'drug-class-first selection  ·  upper-tail hypergeometric',
         '#fce5cd', '#a04a00'),
        (2.86, 'Step 4',
         'Drug–target curation',
         'Therapeutic Target Database  +  OpenTargets (release 2026.03)',
         '#f4cccc', '#922b21'),
        (1.98, 'Step 5',
         '9-point Molecular Prioritization Score',
         'Genomic / context-anchor (0–3)  +  GEO (0–3)  +  '
         'KEGG (0–2)  +  Literature (0–1)',
         '#ead1dc', '#6c3483'),
        (1.10, 'Step 6',
         'Independent PubMed prior-proposal audit',
         'Urologic-oncology-literature-only novelty classification '
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
    ax.text(5.50, 0.72, 'Master Table 1 — 30 Drug–Cancer Associations',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='#7a4a00')
    ax.text(2.20, 0.40, '18  previously proposed',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#0b2e4f')
    ax.text(2.20, 0.20, '(convergent literature support)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#0b2e4f')
    ax.text(4.85, 0.40, '6  framework-novel',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#c00000')
    ax.text(4.85, 0.20, '(within urologic-oncology literature)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#c00000')
    ax.text(7.30, 0.40, '5  partially novel',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#6c3483')
    ax.text(7.30, 0.20, '(variant-specific extensions)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#6c3483')
    ax.text(9.50, 0.40, '1  negative biomarker',
            ha='center', va='center', fontsize=8.5, weight='bold',
            color='#1d4d33')
    ax.text(9.50, 0.20, '(TROP2-low in Sarc-UC)',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#1d4d33')

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
xl_path = Path(r"C:\Users\garre\framework_expansion\data\GSE180999_DE.xlsx")
rmc2c = pd.read_excel(xl_path, sheet_name='RMC2C+SMARCB1')
rmc219 = pd.read_excel(xl_path, sheet_name='RMC219+SMARCB1')
rmc2c.columns = ['gene', 'l2fc_12h_RMC2C', 'q_12h_RMC2C',
                  'l2fc_48h_RMC2C', 'q_48h_RMC2C']
rmc219.columns = ['gene', 'l2fc_12h_RMC219', 'q_12h_RMC219',
                   'l2fc_48h_RMC219', 'q_48h_RMC219']
de = pd.merge(rmc2c, rmc219, on='gene').dropna(
    subset=['l2fc_48h_RMC2C', 'q_48h_RMC2C', 'l2fc_48h_RMC219', 'q_48h_RMC219'])
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
for _, r in highlight.iterrows():
    g = r['gene']
    x = -r['l2fc_48h_RMC2C']  # flip sign for disease-state orientation
    y = -np.log10(max(r['q_48h_RMC2C'], 1e-300))
    if g in ['IL8', 'CXCL1', 'CXCL2', 'HBEGF', 'CEACAM1']:
        axA.annotate(g, (x, y), xytext=(x + 0.3, y + 5), fontsize=7,
                     fontweight='bold', color='darkred')
axA.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.set_xlabel('log₂FC (SMARCB1-null vs SMARCB1-rescue, RMC-2C cells)\n'
               '← DOWN in RMC         UP in RMC →')
axA.set_ylabel('−log₁₀(adj. p-value)')
axA.set_title('A. Volcano plot — RMC-2C cell line\n'
              'GSE180999 (n=9; SMARCB1-null vs rescue)',
              fontsize=9.5, pad=8)
axA.set_xlim(-9, 3)

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
axA.set_ylabel('−log₁₀(adj. p-value)')
axA.set_xlim(-3.0, 2.5)
axA.set_title('A. Volcano — Sarcomatoid UC (n=28) vs conventional UC (n=84)\n'
              'GSE128192; novel targets red, negative biomarker blue',
              fontsize=9.5, pad=8)

enr_all = json.load(open(RESULTS / 'kegg_enrichment_all_diseases.json'))
sarc_enr = enr_all['SarcUC']
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
for i, (v, o) in enumerate(zip(pvals, overlaps)):
    axB.text(v + xmax * 0.02, i, f'k = {o}', fontsize=7.5,
             va='center', ha='left', color='#333')
axB.grid(axis='x', alpha=0.3)

panel_c_schematic(axC, SCHEMATICS / 'Figure3_PanelC_SarcUC.png',
                  'C. Proposed cellular mechanism — Sarcomatoid UC framework-'
                  'novel targets + TROP2-low negative biomarker')

plt.suptitle('Figure 3. Sarcomatoid Urothelial Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure3_SarcUC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure3_SarcUC.png ({(FIGURES/'Figure3_SarcUC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 4 — SCBC
# =====================================================================
print("\nGenerating Figure 4: SCBC (panels A/B matplotlib + Panel C ChatGPT)")
scbc_subtypes = pd.read_csv(RESULTS / 'SCBC_subtype_calls.csv')
ascl1_df = pd.read_csv(RESULTS / 'SCBC_up_in_ASCL1.csv').head(10)
neur_df  = pd.read_csv(RESULTS / 'SCBC_up_in_NEUROD1.csv').head(10)

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.30],
                       hspace=0.45, wspace=0.45,
                       left=0.08, right=0.97, top=0.93, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

counts = scbc_subtypes['subtype'].value_counts()
colors_pie = ['#3498db', '#9b59b6', '#e67e22', '#27ae60']
axA.pie(counts.values, labels=counts.index,
        colors=colors_pie[:len(counts)],
        autopct=lambda p: f'n={int(p*counts.sum()/100)}\n({p:.0f}%)',
        startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
axA.set_title('A. SCBC subtype distribution (n=44)\n'
              'classified by maximum lineage-TF expression — GSE269750',
              fontsize=9.5, pad=8)

ascl1_top = ascl1_df.head(8).copy()
ascl1_top['subtype'] = 'ASCL1+'
neur_top  = neur_df.head(8).copy()
neur_top['subtype'] = 'NEUROD1+'
n_neur, n_ascl = len(neur_top), len(ascl1_top)
gap = 1.5
neur_y = np.arange(n_neur)[::-1] + 0.5
ascl_y = np.arange(n_ascl)[::-1] + 0.5 + n_neur + gap

for i, (_, r) in enumerate(ascl1_top.iterrows()):
    is_headline = (r['gene'] == 'CEACAM5')
    color = '#922b21' if is_headline else '#3498db'
    axB.barh(ascl_y[i], r['log2fc'], color=color, edgecolor='black',
             linewidth=0.4, height=0.7)
for i, (_, r) in enumerate(neur_top.iterrows()):
    is_headline = (r['gene'] == 'SSTR2')
    color = '#922b21' if is_headline else '#9b59b6'
    axB.barh(neur_y[i], r['log2fc'], color=color, edgecolor='black',
             linewidth=0.4, height=0.7)

axB.set_yticks(list(ascl_y) + list(neur_y))
axB.set_yticklabels(list(ascl1_top['gene']) + list(neur_top['gene']),
                    fontsize=7.8)
axB.set_xlabel('log₂FC (subtype vs other subtypes)')
axB.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axB.grid(axis='x', alpha=0.3)
divider_y = n_neur + gap / 2
axB.axhline(divider_y, color='#888', lw=0.6, alpha=0.5)
axB.text(0.98, 0.97, 'ASCL1+  ·  CEACAM5 (red)',
         ha='right', va='top', transform=axB.transAxes,
         fontsize=8, weight='bold', color='#3498db',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#e8f0f9',
                   edgecolor='#3498db', linewidth=0.8))
axB.text(0.98, 0.45, 'NEUROD1+  ·  SSTR2 (red)',
         ha='right', va='top', transform=axB.transAxes,
         fontsize=8, weight='bold', color='#9b59b6',
         bbox=dict(boxstyle='round,pad=0.3', facecolor='#efe6f5',
                   edgecolor='#9b59b6', linewidth=0.8))
axB.set_title('B. Headline subtype-stratified upregulated genes\n'
              'CEACAM5 (ASCL1+) and SSTR2 (NEUROD1+) highlighted dark red',
              fontsize=9.5, pad=8)

panel_c_schematic(axC, SCHEMATICS / 'Figure4_PanelC_SCBC.png',
                  'C. Proposed cellular mechanism — Lineage-stratified SCBC '
                  'framework-novel cell-surface targets')

plt.suptitle('Figure 4. Small-Cell Bladder Cancer — Lineage-Stratified Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure4_SCBC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure4_SCBC.png ({(FIGURES/'Figure4_SCBC.png').stat().st_size:,} bytes)")

print("\nAll three figures regenerated with ChatGPT cellular schematics.")
