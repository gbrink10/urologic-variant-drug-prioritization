"""Generate final Figures 2, 3, 4 with integrated cellular mechanism
schematics replacing the redundant chart/panel content.

Layout (consistent across all three figures):
  Panel A (top-left): volcano / subtype distribution
  Panel B (top-right): cross-cell-line or pathway enrichment or subtype bars
  Panel C (full-width bottom): cellular mechanism schematic
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import (FancyBboxPatch, Circle, Ellipse, Polygon,
                                  FancyArrowPatch)
sys.stdout.reconfigure(encoding='utf-8')

RESULTS = Path(r"C:\Users\garre\framework_expansion\results")
FIGURES = Path(r"C:\Users\garre\framework_expansion\figures")

plt.rcParams.update({
    'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
    'font.family': 'sans-serif',
    'axes.spines.top': False, 'axes.spines.right': False,
})


# =====================================================================
# Schematic helper functions
# =====================================================================
def smooth_blob(cx, cy, rx, ry, n=80, wiggle=0.10, seed=0):
    rng = np.random.RandomState(seed)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    r_mod = (1 + wiggle * np.cos(theta * 4 + rng.uniform(0, 2 * np.pi))
                + 0.5 * wiggle * np.cos(theta * 7 + rng.uniform(0, 2 * np.pi)))
    xs = cx + rx * r_mod * np.cos(theta)
    ys = cy + ry * r_mod * np.sin(theta)
    return list(zip(xs, ys))


def draw_receptor(ax, x, y, size=0.28, color='#222', angle=90, lw=1.8):
    rad = np.radians(angle)
    dx, dy = np.cos(rad), np.sin(rad)
    sx, sy = x + size * dx, y + size * dy
    ax.plot([x, sx], [y, sy], color=color, lw=lw, solid_capstyle='round',
            zorder=5)
    for arm_off in (-45, 45):
        arad = np.radians(angle + arm_off)
        ax_ = sx + 0.7 * size * np.cos(arad)
        ay_ = sy + 0.7 * size * np.sin(arad)
        ax.plot([sx, ax_], [sy, ay_], color=color, lw=lw,
                solid_capstyle='round', zorder=5)


def draw_inhibition(ax, start, end, color='darkred', lw=1.8, bar_half=0.20):
    sx, sy = start
    ex, ey = end
    ax.plot([sx, ex], [sy, ey], color=color, lw=lw, solid_capstyle='round',
            zorder=8)
    dx, dy = ex - sx, ey - sy
    L = np.hypot(dx, dy)
    if L == 0:
        return
    px, py = -dy / L, dx / L
    ax.plot([ex - bar_half * px, ex + bar_half * px],
            [ey - bar_half * py, ey + bar_half * py],
            color=color, lw=lw + 0.7, solid_capstyle='round', zorder=8)


def draw_drug_box(ax, x, y, w, h, label_main, label_sub, novel=True):
    ec = 'darkred' if novel else '#444'
    fc = '#fadbd8' if novel else '#ececec'
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                  ec=ec, fc=fc, linewidth=1.5, zorder=6))
    ax.text(x + w/2, y + h * 0.65, label_main, ha='center', va='center',
            fontsize=8.5, weight='bold', color=ec, zorder=7)
    ax.text(x + w/2, y + h * 0.30, label_sub, ha='center', va='center',
            fontsize=7.3, color=ec, zorder=7)


def draw_phenotype_box(ax, x, y, w, h, main, sub=None, accent='#806600'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                  ec=accent, fc='#fff8e1', linewidth=1.3,
                                  zorder=6))
    ax.text(x + w/2, y + (h*0.65 if sub else h*0.5), main,
            ha='center', va='center', fontsize=8.5, weight='bold',
            color=accent, zorder=7)
    if sub:
        ax.text(x + w/2, y + h * 0.28, sub, ha='center', va='center',
                fontsize=7.3, color='#1a1a1a', zorder=7)


# =====================================================================
# Three schematics (each takes an ax, draws into it)
# =====================================================================
def schematic_rmc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 10); ax.axis('off')
    ax.text(11, 9.6,
            'C. Proposed mechanism — RMC chemokine axis and framework-novel drug-class candidates',
            ha='center', va='center', fontsize=10.5, weight='bold')

    # Drug boxes top
    draw_drug_box(ax, 1.0, 8.3, 6.0, 0.85,
                  'FRAMEWORK-NOVEL: anti-CEACAM1',
                  'CM24 (Phase I/II)')
    draw_drug_box(ax, 10.0, 8.3, 8.0, 0.85,
                  'FRAMEWORK-NOVEL: CXCR1 / CXCR2 antagonists',
                  'reparixin · navarixin (MK-7123) · AZD5069 · danirixin · ladarixin')

    # RMC cell
    ax.add_patch(Polygon(smooth_blob(4.5, 4.6, 3.5, 2.4, seed=7),
                          closed=True, facecolor='#f8d7da', edgecolor='#922b21',
                          linewidth=1.8, alpha=0.85))
    ax.text(4.5, 7.5, 'SMARCB1-null RMC tumor cell',
            ha='center', va='center', fontsize=9.5, weight='bold',
            color='#922b21', style='italic')

    # Nucleus + SMARCB1-X
    ax.add_patch(Ellipse((3.5, 4.4), 1.9, 1.3, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.2))
    ax.text(3.5, 4.75, 'Nucleus', ha='center', va='center',
            fontsize=7.3, style='italic', color='#1f3a5c')
    ax.text(3.5, 4.20, 'SMARCB1', ha='center', va='center',
            fontsize=8.3, weight='bold', color='#1f3a5c')
    ax.plot([2.75, 4.25], [4.65, 3.85], color='#c00', lw=2.2, zorder=5)
    ax.plot([2.75, 4.25], [3.85, 4.65], color='#c00', lw=2.2, zorder=5)

    # CEACAM1 on RMC right edge
    draw_receptor(ax, 7.5, 4.6, size=0.32, color='#7a4a00', angle=0)
    ax.text(7.95, 4.30, 'CEACAM1',
            fontsize=7.8, weight='bold', color='#7a4a00', zorder=7)

    # Chemokines
    chemokines = [(5.7, 6.2, 'IL-8'), (5.7, 4.7, 'CXCL1'), (5.7, 3.2, 'CXCL2')]
    for cx, cy, lbl in chemokines:
        ax.add_patch(Circle((cx, cy), 0.16, facecolor='#c00', edgecolor='black',
                             linewidth=0.6, alpha=0.85, zorder=4))
        ax.text(cx, cy + 0.45, lbl, ha='center', va='center',
                fontsize=7, weight='bold', color='#c00')
    for sy in (6.2, 4.7, 3.2):
        ax.annotate('', xy=(8.4, sy), xytext=(5.95, sy),
                    arrowprops=dict(arrowstyle='->', lw=1.4,
                                    color='#c00', alpha=0.7))

    # Myeloid cell
    ax.add_patch(Polygon(smooth_blob(14.5, 4.6, 3.2, 2.3, seed=11),
                          closed=True, facecolor='#fff3cd', edgecolor='#806600',
                          linewidth=1.8, alpha=0.85))
    ax.text(14.5, 7.4, 'Myeloid cell (MDSC precursor)',
            ha='center', va='center', fontsize=9.5, weight='bold',
            color='#806600', style='italic')
    ax.add_patch(Ellipse((14.5, 4.6), 1.5, 1.0, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.0, alpha=0.7))

    for ry, rname in [(5.5, 'CXCR1'), (3.7, 'CXCR2')]:
        draw_receptor(ax, 11.5, ry, size=0.32, color='#1d4d33', angle=180)
        ax.text(11.05, ry, rname, ha='right', va='center',
                fontsize=8, weight='bold', color='#1d4d33', zorder=7)

    # Inhibition arrows
    draw_inhibition(ax, (11.6, 8.3), (11.55, 5.78), color='darkred', lw=1.8)
    draw_inhibition(ax, (13.0, 8.3), (11.55, 3.98), color='darkred', lw=1.8)
    draw_inhibition(ax, (5.5, 8.3), (7.4, 5.0), color='darkred', lw=1.8)

    # Output boxes
    draw_phenotype_box(ax, 18.5, 5.2, 3.4, 2.0,
                        'MDSC recruitment',
                        '+ immunosuppressive\ntumor microenvironment',
                        accent='#806600')
    draw_phenotype_box(ax, 18.5, 2.2, 3.4, 2.0,
                        'Tumor growth +',
                        'reduced anti-tumor\nimmunity',
                        accent='#7a1a00')

    ax.annotate('', xy=(18.5, 6.0), xytext=(17.0, 5.0),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#806600'))
    ax.annotate('', xy=(20.2, 4.2), xytext=(20.2, 5.2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#7a1a00'))

    ax.add_patch(FancyBboxPatch((0.2, 0.05), 21.6, 0.32,
                                  boxstyle="round,pad=0.03",
                                  ec='#888', fc='#f4f4f4', linewidth=0.8))
    ax.text(11, 0.21,
            '⊥ = drug inhibition  ·  Y = membrane receptor  ·  ● = secreted chemokine  ·  red = framework-novel target',
            ha='center', va='center', fontsize=7.5, style='italic', color='#333')


def schematic_sarcuc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(11, 10.5,
            'C. Proposed mechanism — Sarcomatoid UC framework-novel targets + TROP2-low negative biomarker',
            ha='center', va='center', fontsize=10.5, weight='bold')

    ax.add_patch(Polygon(smooth_blob(11, 5.2, 5.0, 3.2, seed=21),
                          closed=True, facecolor='#e8d8e8', edgecolor='#6c3483',
                          linewidth=1.8, alpha=0.85))
    ax.text(11, 9.0, 'Sarcomatoid urothelial carcinoma cell',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#6c3483', style='italic')

    ax.add_patch(Ellipse((10, 5.2), 4.5, 2.6, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.2))
    ax.text(10, 6.85, 'Nucleus', ha='center', va='center',
            fontsize=7.5, style='italic', color='#1f3a5c')
    ax.add_patch(Circle((8.5, 5.7), 0.45, facecolor='#fadbd8', ec='#922b21', lw=1.2))
    ax.text(8.5, 5.7, 'NSD2', ha='center', va='center', fontsize=7.5, weight='bold', color='#922b21')
    ax.add_patch(Circle((10.0, 5.7), 0.45, facecolor='#fadbd8', ec='#922b21', lw=1.2))
    ax.text(10.0, 5.7, 'UHRF1', ha='center', va='center', fontsize=7.5, weight='bold', color='#922b21')
    ax.add_patch(Ellipse((11.7, 5.7), 1.1, 0.55, facecolor='#fadbd8', ec='#922b21', lw=1.2))
    ax.text(11.7, 5.7, 'ATR-ATRIP', ha='center', va='center',
            fontsize=7.5, weight='bold', color='#922b21')
    ax.text(10, 4.5, 'Epigenetic dysregulation  +  DNA damage response',
            ha='center', va='center', fontsize=7, style='italic', color='#1f3a5c')

    ax.add_patch(Circle((13.4, 3.4), 0.45, facecolor='#fce5cd', ec='#a04a00', lw=1.2))
    ax.text(13.4, 3.4, 'G6PD', ha='center', va='center', fontsize=7.5, weight='bold', color='#a04a00')
    ax.text(13.4, 2.85, 'pentose phosphate\npathway', ha='center', va='center',
            fontsize=6.5, style='italic', color='#a04a00')

    draw_receptor(ax, 6.5, 5.2, size=0.35, color='#1d3a8a', angle=180, lw=2.0)
    ax.text(6.0, 6.05, 'TROP2', ha='right', va='center',
            fontsize=8.5, weight='bold', color='#1d3a8a', zorder=7)
    ax.text(6.0, 5.75, '(LOW)', ha='right', va='center',
            fontsize=7.3, weight='bold', color='#c00', style='italic',
            zorder=7)

    draw_drug_box(ax, 0.5, 8.4, 4.0, 0.85,
                  'FRAMEWORK-NOVEL: NSD2 inhibitor',
                  'KTX-1001 (Phase I)')
    draw_inhibition(ax, (2.5, 8.4), (8.5, 6.05), color='darkred')

    draw_drug_box(ax, 13.5, 8.4, 7.5, 0.85,
                  'FRAMEWORK-NOVEL: ATR inhibitors',
                  'ceralasertib · berzosertib · elimusertib')
    draw_inhibition(ax, (17.2, 8.4), (12.0, 6.05), color='darkred')

    draw_drug_box(ax, 16.0, 6.3, 5.5, 0.75,
                  'PARTIALLY NOVEL: UHRF1 PROTAC',
                  'UM-002 (preclinical)')
    draw_inhibition(ax, (16.0, 6.55), (10.4, 5.85), color='darkred')

    draw_drug_box(ax, 16.0, 3.0, 5.5, 0.75,
                  'PARTIALLY NOVEL: G6PD inhibitor',
                  '6-aminonicotinamide')
    draw_inhibition(ax, (16.0, 3.35), (13.85, 3.35), color='darkred')

    ax.add_patch(FancyBboxPatch((0.2, 3.0), 4.5, 0.85,
                                  boxstyle="round,pad=0.05",
                                  ec='#1d3a8a', fc='#d6e4f0', linewidth=1.5,
                                  zorder=6))
    ax.text(2.45, 3.65, 'NEGATIVE BIOMARKER',
            ha='center', va='center', fontsize=8.5, weight='bold', color='#1d3a8a',
            zorder=7)
    ax.text(2.45, 3.25, 'sacituzumab govitecan → predicted non-response',
            ha='center', va='center', fontsize=7.3, color='#1d3a8a', zorder=7)
    ax.annotate('', xy=(6.3, 5.0), xytext=(4.7, 3.7),
                arrowprops=dict(arrowstyle='->', lw=1.4, color='#1d3a8a',
                                ls='dashed'))
    ax.plot([6.05, 6.55], [4.75, 5.25], color='#c00', lw=2.2, zorder=10)
    ax.plot([6.05, 6.55], [5.25, 4.75], color='#c00', lw=2.2, zorder=10)

    draw_phenotype_box(ax, 0.2, 0.45, 7.0, 1.5,
                        'Epigenetic dysregulation reversal +',
                        'DNA damage repair vulnerability',
                        accent='#922b21')
    draw_phenotype_box(ax, 7.8, 0.45, 6.4, 1.5,
                        'Metabolic reprogramming',
                        'pentose phosphate pathway',
                        accent='#a04a00')
    draw_phenotype_box(ax, 14.8, 0.45, 6.8, 1.5,
                        'TROP2-low → de-prioritize',
                        'sacituzumab govitecan',
                        accent='#1d3a8a')


def schematic_scbc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(11, 10.5,
            'C. Proposed mechanism — Lineage-stratified SCBC framework-novel cell-surface targets',
            ha='center', va='center', fontsize=10.5, weight='bold')

    ax.add_patch(Polygon(smooth_blob(5.5, 5.0, 3.3, 2.6, seed=31),
                          closed=True, facecolor='#cfe0f5', edgecolor='#1f4e79',
                          linewidth=1.8, alpha=0.85))
    ax.text(5.5, 8.2, 'ASCL1-positive SCBC cell',
            ha='center', va='center', fontsize=9.5, weight='bold',
            color='#1f4e79', style='italic')
    ax.add_patch(Ellipse((5.5, 4.8), 1.7, 1.1, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.0, alpha=0.7))
    ax.text(5.5, 4.8, 'ASCL1+', ha='center', va='center',
            fontsize=8, weight='bold', color='#1f3a5c')
    for ry in [6.2, 5.5, 4.5, 3.7]:
        draw_receptor(ax, 8.0, ry, size=0.30, color='#922b21', angle=0, lw=1.8)
    ax.text(8.55, 6.2, 'CEACAM5 HIGH', fontsize=8, weight='bold', color='#922b21',
            zorder=7)

    ax.add_patch(Polygon(smooth_blob(16.5, 5.0, 3.3, 2.6, seed=37),
                          closed=True, facecolor='#e6e6fa', edgecolor='#6c3483',
                          linewidth=1.8, alpha=0.85))
    ax.text(16.5, 8.2, 'NEUROD1-positive SCBC cell',
            ha='center', va='center', fontsize=9.5, weight='bold',
            color='#6c3483', style='italic')
    ax.add_patch(Ellipse((16.5, 4.8), 1.7, 1.1, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.0, alpha=0.7))
    ax.text(16.5, 4.8, 'NEUROD1+', ha='center', va='center',
            fontsize=8, weight='bold', color='#1f3a5c')
    for ry in [6.2, 5.5, 4.5, 3.7]:
        draw_receptor(ax, 14.0, ry, size=0.30, color='#6c3483', angle=180, lw=1.8)
    ax.text(13.55, 6.2, 'SSTR2 HIGH', ha='right', va='center',
            fontsize=8, weight='bold', color='#6c3483', zorder=7)

    draw_drug_box(ax, 0.5, 8.6, 9.5, 0.85,
                  'FRAMEWORK-NOVEL: anti-CEACAM5 ADC',
                  '(tusamitamab ravtansine — discontinued Dec 2023 — replacement-agent required)')
    for ry in [6.2, 5.5, 4.5, 3.7]:
        draw_inhibition(ax, (5.0, 8.6), (8.0, ry + 0.25),
                         color='darkred', lw=1.4, bar_half=0.13)

    draw_drug_box(ax, 12.0, 8.6, 9.5, 0.85,
                  'FRAMEWORK-NOVEL: lutetium-177 DOTATATE (FDA-approved)',
                  '(theranostic — Ga-68 DOTATATE PET selection → Lu-177 therapy)')
    for ry in [6.2, 5.5, 4.5, 3.7]:
        ax.annotate('', xy=(14.0, ry + 0.25), xytext=(17.0, 8.6),
                    arrowprops=dict(arrowstyle='-|>', lw=1.4,
                                    color='#6c3483'))

    cx, cy = 19.0, 5.0
    for ang in np.linspace(0, 2*np.pi, 8, endpoint=False):
        ax.plot([cx, cx + 0.35*np.cos(ang)], [cy, cy + 0.35*np.sin(ang)],
                color='#c00', lw=1.4, alpha=0.7)
    ax.add_patch(Circle((cx, cy), 0.18, facecolor='#c00', edgecolor='black',
                         linewidth=0.6, alpha=0.5, zorder=6))
    ax.text(cx, cy - 0.7, '¹⁷⁷Lu radiation\nlocal cytotoxicity',
            ha='center', va='center', fontsize=7, color='#c00',
            style='italic')

    ax.text(9.5, 3.0, 'ADC payload\n→ apoptosis',
            ha='center', va='center', fontsize=7, color='#922b21',
            style='italic')

    draw_phenotype_box(ax, 0.5, 0.45, 10.0, 1.5,
                        'ASCL1-driven CEA-mediated cytotoxicity',
                        'paradigm transfer from small-cell lung cancer',
                        accent='#1f4e79')
    draw_phenotype_box(ax, 11.5, 0.45, 10.0, 1.5,
                        'NEUROD1-driven peptide receptor radionuclide therapy',
                        'existing Ga-68 / Lu-177 theranostic infrastructure',
                        accent='#6c3483')


# =====================================================================
# Figure 2 — RMC findings (3-panel with mechanism schematic)
# =====================================================================
print("Generating Figure 2: RMC (3-panel + cellular schematic)")
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

fig = plt.figure(figsize=(11, 11))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.05],
                       hspace=0.45, wspace=0.30,
                       left=0.07, right=0.98, top=0.93, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

# Panel A — Volcano
neg_log_q = -np.log10(de['q_48h_RMC2C'].clip(lower=1e-300))
axA.scatter(de['l2fc_48h_RMC2C'], neg_log_q, s=4, c='lightgrey', alpha=0.5)
highlight = de[de['gene'].isin(top_genes)]
axA.scatter(highlight['l2fc_48h_RMC2C'],
            -np.log10(highlight['q_48h_RMC2C'].clip(lower=1e-300)),
            s=30, c='red', edgecolor='black', linewidth=0.5, zorder=5)
for _, r in highlight.iterrows():
    g = r['gene']
    x, y = r['l2fc_48h_RMC2C'], -np.log10(max(r['q_48h_RMC2C'], 1e-300))
    if g in ['IL8', 'CXCL1', 'CXCL2', 'HBEGF', 'CEACAM1']:
        axA.annotate(g, (x, y), xytext=(x - 0.3, y + 5), fontsize=7,
                     fontweight='bold', color='darkred')
axA.axvline(-1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.axhline(-np.log10(0.05), color='red', linestyle='--', lw=0.8, alpha=0.5)
axA.set_xlabel('log₂FC (SMARCB1-rescue vs NEG, RMC-2C cells)\n← UP in SMARCB1-null         DOWN in null →')
axA.set_ylabel('−log₁₀(adj. p-value)')
axA.set_title('A. Volcano plot — RMC-2C cell line\nGSE180999 (n=9; SMARCB1-rescue vs NEG)',
              fontsize=9.5, pad=8)
axA.set_xlim(-3, 9)

# Panel B — Cross-cell-line consistency
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

# Panel C — RMC schematic
schematic_rmc(axC)

plt.suptitle('Figure 2. Renal Medullary Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.985)
plt.savefig(FIGURES / 'Figure2_RMC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: Figure2_RMC.png  ({(FIGURES/'Figure2_RMC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 3 — Sarc-UC findings (3-panel with mechanism schematic)
# =====================================================================
print("\nGenerating Figure 3: Sarc-UC (3-panel + cellular schematic)")
sarc_de = pd.read_csv(RESULTS / 'SarcomatoidUC_DE_full.csv')

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.05],
                       hspace=0.50, wspace=0.30,
                       left=0.07, right=0.98, top=0.92, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

# Panel A — Volcano (dedup + manual offsets)
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
axA.set_title('A. Volcano — Sarcomatoid UC (n=28) vs conventional UC (n=84)\n'
              'GSE128192; novel targets red, negative biomarker blue',
              fontsize=9.5, pad=8)

# Panel B — KEGG enrichment (clean labels)
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

# Panel C — Sarc-UC schematic
schematic_sarcuc(axC)

plt.suptitle('Figure 3. Sarcomatoid Urothelial Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure3_SarcUC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: Figure3_SarcUC.png  ({(FIGURES/'Figure3_SarcUC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 4 — SCBC subtype-stratified (3-panel: pie + ASCL1+/NEUROD1+
# combined headlines + schematic)
# =====================================================================
print("\nGenerating Figure 4: SCBC (3-panel + cellular schematic)")
scbc_subtypes = pd.read_csv(RESULTS / 'SCBC_subtype_calls.csv')
ascl1_df = pd.read_csv(RESULTS / 'SCBC_up_in_ASCL1.csv').head(10)
neur_df  = pd.read_csv(RESULTS / 'SCBC_up_in_NEUROD1.csv').head(10)

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.05],
                       hspace=0.50, wspace=0.30,
                       left=0.07, right=0.98, top=0.92, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

# Panel A — Subtype distribution pie
counts = scbc_subtypes['subtype'].value_counts()
colors_pie = ['#3498db', '#9b59b6', '#e67e22', '#27ae60']
axA.pie(counts.values, labels=counts.index,
        colors=colors_pie[:len(counts)],
        autopct=lambda p: f'n={int(p*counts.sum()/100)}\n({p:.0f}%)',
        startangle=90, textprops={'fontsize': 9, 'weight': 'bold'})
axA.set_title('A. SCBC subtype distribution (n=44)\n'
              'classified by maximum lineage-TF expression — GSE269750',
              fontsize=9.5, pad=8)

# Panel B — Combined ASCL1+ / NEUROD1+ headline bars
# Show top 8 ASCL1+ and top 8 NEUROD1+ side by side, highlighting CEACAM5 and SSTR2
ascl1_top = ascl1_df.head(8).copy()
neur_top  = neur_df.head(8).copy()
ascl1_top['subtype'] = 'ASCL1+'
neur_top['subtype']  = 'NEUROD1+'
combined = pd.concat([
    ascl1_top.assign(group_y=np.arange(len(ascl1_top))[::-1] + 0.5 + len(neur_top) + 1.5),
    neur_top.assign(group_y=np.arange(len(neur_top))[::-1] + 0.5),
])
for _, r in combined.iterrows():
    is_headline = (r['gene'] == 'CEACAM5' and r['subtype'] == 'ASCL1+') or \
                  (r['gene'] == 'SSTR2'   and r['subtype'] == 'NEUROD1+')
    color = '#922b21' if is_headline else (
        '#3498db' if r['subtype'] == 'ASCL1+' else '#9b59b6')
    axB.barh(r['group_y'], r['log2fc'], color=color, edgecolor='black',
             linewidth=0.4, height=0.7)
all_y = combined['group_y'].tolist()
all_labels = combined['gene'].tolist()
axB.set_yticks(all_y)
axB.set_yticklabels(all_labels, fontsize=7.5)
axB.set_xlabel('log₂FC (subtype vs other subtypes)')
axB.axvline(1, color='red', linestyle='--', lw=0.8, alpha=0.5)
axB.grid(axis='x', alpha=0.3)
# Section labels
axB.text(-0.25, len(neur_top) + 1.5 + len(ascl1_top) / 2 + 0.5,
         'ASCL1+\n(CEACAM5)', ha='right', va='center', rotation=90,
         fontsize=8, weight='bold', color='#3498db',
         transform=axB.get_yaxis_transform())
axB.text(-0.25, len(neur_top) / 2 + 0.5,
         'NEUROD1+\n(SSTR2)', ha='right', va='center', rotation=90,
         fontsize=8, weight='bold', color='#9b59b6',
         transform=axB.get_yaxis_transform())
axB.set_title('B. Headline subtype-stratified upregulated genes\n'
              'CEACAM5 (ASCL1+) and SSTR2 (NEUROD1+) highlighted dark red',
              fontsize=9.5, pad=8)

# Panel C — SCBC schematic
schematic_scbc(axC)

plt.suptitle('Figure 4. Small-Cell Bladder Cancer — Lineage-Stratified Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure4_SCBC.png', bbox_inches='tight')
plt.close()
print(f"  Saved: Figure4_SCBC.png  ({(FIGURES/'Figure4_SCBC.png').stat().st_size:,} bytes)")

print("\nAll three figures regenerated with integrated cellular schematics.")
