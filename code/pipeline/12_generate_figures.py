"""Generate the 4 novel-target-focused figures for v26 manuscript.

Fig 1 — Pipeline schematic (6-step workflow diagram)
Fig 2 — RMC novel findings (volcano + chemokine triad + pathway + drug-class)
Fig 3 — Sarcomatoid UC novel findings (volcano + KEGG + TROP2-down + drug-class)
Fig 4 — SCBC subtype-stratified novel findings (4 panels per subtype)

Uses matplotlib; produces high-resolution PNG figures in framework_expansion/figures/
"""
import sys, json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")
FIGURES = Path(r"C:\Users\garre\framework_expansion\figures")
FIGURES.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    'figure.dpi': 200,
    'savefig.dpi': 300,
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'font.family': 'sans-serif',
})

# =====================================================================
# Figure 1 — Pipeline schematic
# =====================================================================
print("Generating Figure 1: Pipeline schematic")
fig, ax = plt.subplots(figsize=(11, 7.5))
ax.set_xlim(0, 11)
ax.set_ylim(0, 7.5)
ax.axis('off')

# Draw 6 step boxes (shifted down to leave clear space for title)
steps = [
    (0.4, 4.2, 'Step 1\nTCGA Pan-Cancer\nAtlas alteration\nfrequencies', '#cfe2f3'),
    (2.2, 4.2, 'Step 2\nGEO transcriptomic\ndata (10 datasets,\n7 contexts)', '#d9ead3'),
    (4.0, 4.2, 'Step 3\nDifferential expr.\n+ KEGG enrichment\n(18 pathways)', '#fff2cc'),
    (5.8, 4.2, 'Step 4\nDrug-target curation\n(TTD + OpenTargets)', '#f4cccc'),
    (7.6, 4.2, 'Step 5\n9-point Molecular\nPrioritization Score\n(T/G/K/L)', '#ead1dc'),
    (9.4, 4.2, 'Step 6\nIndependent PubMed\nliterature audit\n(novelty per row)', '#d0e0e3'),
]
for x, y, txt, color in steps:
    box = FancyBboxPatch((x, y), 1.6, 1.6, boxstyle="round,pad=0.05",
                          ec='black', fc=color, linewidth=1.0)
    ax.add_patch(box)
    ax.text(x + 0.8, y + 0.8, txt, ha='center', va='center', fontsize=8, weight='bold')

# Arrows between steps
for i in range(5):
    ax.annotate('', xy=(steps[i+1][0], steps[i+1][1] + 0.8),
                xytext=(steps[i][0] + 1.6, steps[i][1] + 0.8),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))

# Inputs (top) — clear separation from step boxes
ax.text(5.5, 7.0, '7 Aggressive Urologic Cancer Contexts',
        ha='center', fontsize=12, weight='bold', color='#1a1a1a')
ax.text(5.5, 6.55, 'NEPC  |  MIBC  |  ccRCC  |  RMC  |  PSCC  |  Sarc-UC  |  SCBC',
        ha='center', fontsize=8.5, color='#444444', style='italic')
# Arrow from input header to step boxes
ax.annotate('', xy=(5.5, 5.8), xytext=(5.5, 6.3),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

# Output (bottom)
output_box = FancyBboxPatch((1.0, 0.5), 9.0, 2.5,
                             boxstyle="round,pad=0.1", ec='black',
                             fc='#fef5e7', linewidth=1.5)
ax.add_patch(output_box)
ax.text(5.5, 2.65, 'Master Table 1: 30 Drug–Cancer Associations',
        ha='center', fontsize=11, weight='bold')
ax.text(5.5, 2.20, '24 convergent validation (previously-proposed priorities)',
        ha='center', fontsize=9)
ax.text(5.5, 1.80, '6 framework-novel within urologic-oncology literature',
        ha='center', fontsize=9, color='#c00')
ax.text(5.5, 1.40, '5 partially novel; 1 clinically-actionable negative biomarker',
        ha='center', fontsize=9)
ax.text(5.5, 0.85, '10 Strong-tier | 17 Moderate-tier | 2 Exploratory-tier (Molecular Prioritization Score 0–9)',
        ha='center', fontsize=8, style='italic', color='#555')

# Connect steps to output
ax.annotate('', xy=(5.5, 3.0), xytext=(5.5, 3.95),
            arrowprops=dict(arrowstyle='->', lw=2.0, color='black'))

plt.title('Figure 1. Unified Public-Data Pipeline Schematic for Drug Repurposing Across\n'
          'Seven Aggressive Urologic Cancer Contexts', fontsize=11, weight='bold', pad=8)
plt.tight_layout()
plt.savefig(FIGURES / 'Figure1_pipeline.png', bbox_inches='tight')
plt.close()
print(f"  Saved: {FIGURES / 'Figure1_pipeline.png'}")


# =====================================================================
# Figure 2 — RMC novel findings
# =====================================================================
print("\nGenerating Figure 2: RMC novel findings")
import xml.etree.ElementTree as ET

# Load RMC DE data — both cell lines for cross-cell-line plot
xl_path = Path(r"C:\Users\garre\framework_expansion\data\GSE180999_DE.xlsx")
rmc2c = pd.read_excel(xl_path, sheet_name='RMC2C+SMARCB1')
rmc219 = pd.read_excel(xl_path, sheet_name='RMC219+SMARCB1')
rmc2c.columns = ['gene', 'l2fc_12h_RMC2C', 'q_12h_RMC2C', 'l2fc_48h_RMC2C', 'q_48h_RMC2C']
rmc219.columns = ['gene', 'l2fc_12h_RMC219', 'q_12h_RMC219', 'l2fc_48h_RMC219', 'q_48h_RMC219']
de = pd.merge(rmc2c, rmc219, on='gene').dropna(
    subset=['l2fc_48h_RMC2C', 'q_48h_RMC2C', 'l2fc_48h_RMC219', 'q_48h_RMC219'])

rmc_up = pd.read_csv(RESULTS / 'RMC_up_in_null_state.csv')
top_genes = rmc_up['gene'].tolist()

fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))

# Panel A — Volcano plot RMC2C
ax = axes[0, 0]
# log2FC is "SMARCB1-rescue vs NEG"; we want genes UP in NEG = down upon rescue (negative l2fc)
neg_log_q = -np.log10(de['q_48h_RMC2C'].clip(lower=1e-300))
ax.scatter(de['l2fc_48h_RMC2C'], neg_log_q, s=4, c='lightgrey', alpha=0.5)
# Highlight top genes UP in NULL (= down on rescue = negative l2fc)
highlight = de[de['gene'].isin(top_genes)]
ax.scatter(highlight['l2fc_48h_RMC2C'], -np.log10(highlight['q_48h_RMC2C'].clip(lower=1e-300)),
           s=30, c='red', edgecolor='black', linewidth=0.5, zorder=5)
for _, r in highlight.iterrows():
    g = r['gene']
    x, y = r['l2fc_48h_RMC2C'], -np.log10(max(r['q_48h_RMC2C'], 1e-300))
    if g in ['IL8', 'CXCL1', 'CXCL2', 'HBEGF', 'CEACAM1']:
        ax.annotate(g, (x, y), xytext=(x-0.2, y), fontsize=7, fontweight='bold',
                    color='darkred')
ax.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.set_xlabel('log₂FC (SMARCB1-rescue vs NEG, RMC-2C cells)\n← UP in SMARCB1-null         DOWN in null →')
ax.set_ylabel('−log₁₀(adj. p-value)')
ax.set_title('A. Volcano plot — RMC-2C cell line\nGSE180999 (n=9; SMARCB1-rescue vs NEG)', fontsize=9)
ax.set_xlim(-3, 9)

# Panel B — Cross-cell-line consistency for top 13 UP-in-null genes
ax = axes[0, 1]
top_df = rmc_up.sort_values('mean_l2fc_48h')
y_pos = np.arange(len(top_df))
ax.barh(y_pos - 0.2, -top_df['l2fc_48h_RMC2C'], height=0.4, label='RMC-2C', color='steelblue')
ax.barh(y_pos + 0.2, -top_df['l2fc_48h_RMC219'], height=0.4, label='RMC219', color='lightcoral')
ax.set_yticks(y_pos)
ax.set_yticklabels(top_df['gene'], fontsize=8)
ax.set_xlabel('log₂FC UP in SMARCB1-null state\n(positive = elevated in RMC)')
ax.set_title('B. Cross-cell-line consistency of\nSMARCB1-null UP genes', fontsize=9)
ax.legend(loc='lower right')
ax.axvline(1, color='red', linestyle='--', lw=0.8)
ax.grid(axis='x', alpha=0.3)

# Panel C — Mechanism schematic
ax = axes[1, 0]
ax.set_xlim(-0.3, 10.3)
ax.set_ylim(-0.5, 7.0)
ax.axis('off')
# Top row boxes (SMARCB1 loss → chemokine triad → CXCR1/2)
ax.add_patch(FancyBboxPatch((0.5, 5.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                              ec='black', fc='#fef5e7'))
ax.text(1.75, 6.0, 'SMARCB1\nbiallelic loss', ha='center', va='center', fontsize=9, weight='bold')

ax.add_patch(FancyBboxPatch((3.75, 5.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                              ec='black', fc='#f4cccc'))
ax.text(5.0, 6.0, 'Chemokine triad\nIL-8 / CXCL1 / CXCL2', ha='center', va='center', fontsize=9, weight='bold')

ax.add_patch(FancyBboxPatch((7.0, 5.5), 2.5, 1.0, boxstyle="round,pad=0.05",
                              ec='black', fc='#d9ead3'))
ax.text(8.25, 6.0, 'CXCR1 / CXCR2\non myeloid cells', ha='center', va='center', fontsize=9, weight='bold')

ax.annotate('', xy=(3.75, 6.0), xytext=(3.0, 6.0),
            arrowprops=dict(arrowstyle='->', lw=1.5))
ax.annotate('', xy=(7.0, 6.0), xytext=(6.25, 6.0),
            arrowprops=dict(arrowstyle='->', lw=1.5))

# Middle box — MDSC recruitment
ax.add_patch(FancyBboxPatch((2.0, 2.8), 6.0, 1.0, boxstyle="round,pad=0.05",
                              ec='black', fc='#fff2cc', linewidth=1.5))
ax.text(5.0, 3.3, 'Myeloid-derived suppressor cell recruitment\n+ immunosuppressive tumor microenvironment',
        ha='center', va='center', fontsize=9, weight='bold')

ax.annotate('', xy=(5.0, 3.8), xytext=(8.25, 5.5),
            arrowprops=dict(arrowstyle='->', lw=1.5))

# Bottom box — Framework-novel target (with breathing room from panel edge)
ax.add_patch(FancyBboxPatch((1.0, 0.4), 8.0, 1.4, boxstyle="round,pad=0.05",
                              ec='darkred', fc='#fadbd8', linewidth=2.0))
ax.text(5.0, 1.1, 'FRAMEWORK-NOVEL TARGET\nReparixin  ·  Navarixin  ·  AZD5069  ·  Danirixin',
        ha='center', va='center', fontsize=9.5, weight='bold', color='darkred')

ax.annotate('', xy=(5.0, 1.8), xytext=(5.0, 2.8),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='darkred'))

ax.set_title('C. Proposed mechanism — RMC chemokine axis', fontsize=9, pad=10)

# Panel D — Drug-class clinical-stage table
ax = axes[1, 1]
ax.axis('off')
drug_table_data = [
    ['Drug', 'Target', 'Stage', 'Status'],
    ['Reparixin', 'CXCR1/2', 'Phase II/III', 'Breast cancer trials'],
    ['Navarixin (MK-7123)', 'CXCR2', 'Phase II', 'Active basket trials'],
    ['AZD5069', 'CXCR2', 'Phase II', 'HNSCC, mCRPC'],
    ['Danirixin', 'CXCR2', 'Phase II', 'Inflammation'],
    ['Ladarixin', 'CXCR1/2', 'Phase II', 'T1 diabetes basket'],
    ['CM24', 'CEACAM1', 'Phase I/II', 'Melanoma + GI'],
]
table = ax.table(cellText=drug_table_data, loc='center',
                  cellLoc='left', colWidths=[0.25, 0.20, 0.20, 0.35])
table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1, 1.6)
for i in range(len(drug_table_data)):
    for j in range(4):
        if i == 0:
            table[(i, j)].set_facecolor('#cfe2f3')
            table[(i, j)].set_text_props(weight='bold')
ax.set_title('D. Candidate drugs for RMC framework-novel targets', fontsize=9)

plt.suptitle('Figure 2. Renal Medullary Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=1.00)
plt.tight_layout()
plt.savefig(FIGURES / 'Figure2_RMC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: {FIGURES / 'Figure2_RMC.png'}")


# =====================================================================
# Figure 3 — Sarcomatoid UC novel findings
# =====================================================================
print("\nGenerating Figure 3: Sarcomatoid UC novel findings")
sarc_de = pd.read_csv(RESULTS / 'SarcomatoidUC_DE_full.csv')
sarc_up = pd.read_csv(RESULTS / 'SarcomatoidUC_up.csv')
sarc_down = pd.read_csv(RESULTS / 'SarcomatoidUC_down.csv')

fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))

# Panel A — Volcano plot
ax = axes[0, 0]
ax.scatter(sarc_de['log2fc'], -np.log10(sarc_de['qvalue'].clip(lower=1e-30)),
           s=3, c='lightgrey', alpha=0.4)
novel_targets = ['WHSC1', 'ATRIP', 'UHRF1', 'G6PD', 'PHC2']
neg_target = ['TACSTD2']
for tgt, col in [(novel_targets, 'red'), (neg_target, 'blue')]:
    sub = sarc_de[sarc_de['gene'].isin(tgt)]
    ax.scatter(sub['log2fc'], -np.log10(sub['qvalue'].clip(lower=1e-30)),
               s=60, c=col, edgecolor='black', linewidth=0.5, zorder=10)
    for _, r in sub.iterrows():
        ax.annotate(r['gene'], (r['log2fc'], -np.log10(max(r['qvalue'], 1e-30))),
                    xytext=(r['log2fc'] + 0.15, -np.log10(max(r['qvalue'], 1e-30)) + 0.5),
                    fontsize=8, fontweight='bold', color=col)
ax.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
ax.set_xlabel('log₂FC (Sarcomatoid UC vs conventional UC)\n← DOWN in sarcomatoid     UP in sarcomatoid →')
ax.set_ylabel('−log₁₀(adj. p-value)')
ax.set_title('A. Volcano — Sarcomatoid UC (n=28) vs conventional UC (n=84)\nGSE128192; novel targets red, negative biomarker blue', fontsize=9)

# Panel B — KEGG enrichment
ax = axes[0, 1]
enr_all = json.load(open(RESULTS / 'kegg_enrichment_all_diseases.json'))
sarc_enr = enr_all['SarcUC']
top_paths = sorted([(p, r['pvalue'], r['overlap']) for p, r in sarc_enr.items() if r['overlap'] > 0],
                   key=lambda x: x[1])[:8]
names = [p for p, _, _ in top_paths]
pvals = [-np.log10(p) for _, p, _ in top_paths]
overlaps = [o for _, _, o in top_paths]
colors = ['darkred' if -np.log10(p) > 1 else 'steelblue' for _, p, _ in top_paths]
ax.barh(range(len(names)), pvals, color=colors)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=8)
ax.set_xlabel('−log₁₀(p-value), hypergeometric')
ax.set_title('B. KEGG pathway enrichment (Sarcomatoid UP)\nEpigenetic Regulation top enriched', fontsize=9)
ax.axvline(-np.log10(0.10), color='red', linestyle='--', lw=0.8, alpha=0.5)
for i, (p, _, o) in enumerate(top_paths):
    ax.text(pvals[i] + 0.05, i, f'k={o}', fontsize=7, va='center')

# Panel C — TROP2 negative biomarker
ax = axes[1, 0]
# Get top 10 most DOWN genes
top_down = sarc_down.head(15)
y_pos = np.arange(len(top_down))[::-1]
colors_down = ['darkblue' if g == 'TACSTD2' else 'lightblue' for g in top_down['gene']]
ax.barh(y_pos, top_down['log2fc'], color=colors_down, edgecolor='black', linewidth=0.4)
ax.set_yticks(y_pos)
ax.set_yticklabels(top_down['gene'], fontsize=8)
ax.set_xlabel('log₂FC Sarcomatoid vs conventional UC')
ax.set_title('C. Top genes DOWN in Sarcomatoid UC\nTROP2/TACSTD2 = sacituzumab govitecan target', fontsize=9)
ax.axvline(-1, color='red', linestyle='--', lw=0.8)

# Panel D — Drug-class clinical-stage table
ax = axes[1, 1]
ax.axis('off')
drug_data = [
    ['Drug', 'Target', 'Stage', 'Novelty'],
    ['KTX-1001', 'NSD2/WHSC1', 'Phase I', 'FRAMEWORK-NOVEL'],
    ['Seclidemstat (SP-2577)', 'NSD2/WHSC1', 'Phase I', 'FRAMEWORK-NOVEL'],
    ['Ceralasertib (AZD6738)', 'ATR', 'Phase II', 'FRAMEWORK-NOVEL'],
    ['Berzosertib (M6620)', 'ATR', 'Phase II', 'FRAMEWORK-NOVEL'],
    ['Elimusertib (BAY-1895344)', 'ATR', 'Phase II', 'FRAMEWORK-NOVEL'],
    ['UM-002 (PROTAC)', 'UHRF1', 'Preclinical', 'Partially novel'],
    ['6-Aminonicotinamide', 'G6PD/PPP', 'Preclinical', 'Partially novel'],
    ['Sacituzumab govitecan', 'TROP2 (NEG)', 'FDA-approved', 'Negative biomarker'],
]
table = ax.table(cellText=drug_data, loc='center',
                  cellLoc='left', colWidths=[0.32, 0.22, 0.20, 0.26])
table.auto_set_font_size(False)
table.set_fontsize(7.5)
table.scale(1, 1.6)
for j in range(4):
    table[(0, j)].set_facecolor('#cfe2f3')
    table[(0, j)].set_text_props(weight='bold')
# Highlight framework-novel rows
for i in [1, 2, 3, 4, 5]:
    for j in range(4):
        table[(i, j)].set_facecolor('#fadbd8')
# Negative biomarker
for j in range(4):
    table[(8, j)].set_facecolor('#d4e6f1')
ax.set_title('D. Candidate drugs for Sarcomatoid UC framework-novel targets', fontsize=9)

plt.suptitle('Figure 3. Sarcomatoid Urothelial Carcinoma — Framework-Novel Findings\n'
             '(NSD2, ATR, UHRF1, G6PD upregulated; TROP2 negative biomarker)',
             fontsize=12, weight='bold', y=1.00)
plt.tight_layout()
plt.savefig(FIGURES / 'Figure3_SarcUC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: {FIGURES / 'Figure3_SarcUC.png'}")


# =====================================================================
# Figure 4 — SCBC subtype-stratified novel findings
# =====================================================================
print("\nGenerating Figure 4: SCBC subtype novel findings")
scbc_subtypes = pd.read_csv(RESULTS / 'SCBC_subtype_calls.csv')

fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))

# Panel A — Subtype distribution
ax = axes[0, 0]
counts = scbc_subtypes['subtype'].value_counts()
colors_pie = ['#3498db', '#e67e22', '#9b59b6', '#27ae60']
wedges, texts, autotexts = ax.pie(
    counts.values, labels=counts.index,
    colors=colors_pie[:len(counts)],
    autopct=lambda p: f'n={int(p*counts.sum()/100)}\n({p:.0f}%)',
    startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
ax.set_title('A. SCBC subtype distribution (n=44)\nClassified by maximum lineage-TF expression\nGSE269750', fontsize=9)

# Panel B — ASCL1+ CEACAM5
ax = axes[0, 1]
ascl1_df = pd.read_csv(RESULTS / 'SCBC_up_in_ASCL1.csv').head(10)
genes_a = ascl1_df['gene'][:10][::-1]
fcs_a = ascl1_df['log2fc'][:10][::-1]
colors_a = ['darkred' if g == 'CEACAM5' else 'steelblue' for g in genes_a]
ax.barh(range(len(genes_a)), fcs_a, color=colors_a)
ax.set_yticks(range(len(genes_a)))
ax.set_yticklabels(genes_a, fontsize=8)
ax.set_xlabel('log₂FC (ASCL1+ vs other subtypes)')
ax.set_title('B. ASCL1+ subtype (n=19) top UP genes\nCEACAM5 = tusamitamab ravtansine target', fontsize=9)
ax.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)

# Panel C — NEUROD1+ SSTR2
ax = axes[1, 0]
neur_df = pd.read_csv(RESULTS / 'SCBC_up_in_NEUROD1.csv').head(10)
genes_n = neur_df['gene'][:10][::-1]
fcs_n = neur_df['log2fc'][:10][::-1]
colors_n = ['darkred' if g == 'SSTR2' else 'mediumpurple' for g in genes_n]
ax.barh(range(len(genes_n)), fcs_n, color=colors_n)
ax.set_yticks(range(len(genes_n)))
ax.set_yticklabels(genes_n, fontsize=8)
ax.set_xlabel('log₂FC (NEUROD1+ vs other subtypes)')
ax.set_title('C. NEUROD1+ subtype (n=10) top UP genes\nSSTR2 → ¹⁷⁷Lu-DOTATATE theranostic target', fontsize=9)
ax.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)

# Panel D — POU2F3+ COX-1
ax = axes[1, 1]
pou_df = pd.read_csv(RESULTS / 'SCBC_up_in_POU2F3.csv').head(10)
genes_p = pou_df['gene'][:10][::-1]
fcs_p = pou_df['log2fc'][:10][::-1]
colors_p = ['darkred' if g in ('PTGS1', 'PLA2G4A') else 'darkorange' for g in genes_p]
ax.barh(range(len(genes_p)), fcs_p, color=colors_p)
ax.set_yticks(range(len(genes_p)))
ax.set_yticklabels(genes_p, fontsize=8)
ax.set_xlabel('log₂FC (POU2F3+ vs other subtypes)')
ax.set_title('D. POU2F3+ subtype (n=7) top UP genes\nPTGS1 (COX-1) + PLA2G4A → aspirin/celecoxib', fontsize=9)
ax.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)

plt.suptitle('Figure 4. Small-Cell Bladder Cancer — Lineage-Transcription-Factor-Stratified\n'
             'Framework-Novel Drug-Target Candidates per Subtype',
             fontsize=12, weight='bold', y=1.00)
plt.tight_layout()
plt.savefig(FIGURES / 'Figure4_SCBC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: {FIGURES / 'Figure4_SCBC.png'}")

print("\nAll 4 figures generated.")
print(f"Output directory: {FIGURES}")
