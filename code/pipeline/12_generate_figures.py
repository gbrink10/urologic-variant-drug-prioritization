"""Final-quality Figures 2/3/4 with integrated cellular mechanism
schematics. Key improvements over prior version:
  - Smoother cell outlines (subtle wiggle)
  - Receptors placed EXACTLY on the cell membrane via parametric angle
    sampling against the same blob function
  - Larger drug boxes sized for the text inside (no overflow)
  - Arrow routes go around labels, not through them
  - Output phenotype boxes visually connected to cells
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
# Cell-membrane geometry helpers
# =====================================================================
def cell_outline_smooth(cx, cy, rx, ry, n=200):
    """Smooth elliptical blob (subtle wiggle for organic feel without
    making the cell look lumpy)."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    # Very small wiggle to keep the cell looking smooth/cell-like
    r_mod = 1 + 0.025 * np.cos(theta * 3) + 0.015 * np.cos(theta * 7)
    xs = cx + rx * r_mod * np.cos(theta)
    ys = cy + ry * r_mod * np.sin(theta)
    return list(zip(xs, ys))


def membrane_point(cx, cy, rx, ry, angle_deg):
    """Return (x, y) point ON the cell membrane at given angle from cell
    center. Uses the same smooth-blob math as cell_outline_smooth."""
    theta = np.radians(angle_deg)
    r_mod = 1 + 0.025 * np.cos(theta * 3) + 0.015 * np.cos(theta * 7)
    return (cx + rx * r_mod * np.cos(theta),
            cy + ry * r_mod * np.sin(theta))


def draw_receptor(ax, x, y, size=0.30, color='#222', angle=90, lw=1.9):
    """Draw a Y-shape receptor pointing outward at `angle` from horizontal.
    (x, y) is the receptor's base on the membrane."""
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


def draw_inhibition(ax, start, end, color='darkred', lw=1.8, bar_half=0.20,
                    zorder=8):
    sx, sy = start
    ex, ey = end
    ax.plot([sx, ex], [sy, ey], color=color, lw=lw, solid_capstyle='round',
            zorder=zorder)
    dx, dy = ex - sx, ey - sy
    L = np.hypot(dx, dy)
    if L == 0:
        return
    px, py = -dy / L, dx / L
    ax.plot([ex - bar_half * px, ex + bar_half * px],
            [ey - bar_half * py, ey + bar_half * py],
            color=color, lw=lw + 0.7, solid_capstyle='round', zorder=zorder)


def draw_drug_box(ax, x, y, w, h, label_main, label_sub, novel=True,
                  fontsize_main=8.5, fontsize_sub=7.3):
    ec = 'darkred' if novel else '#444'
    fc = '#fadbd8' if novel else '#ececec'
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                  ec=ec, fc=fc, linewidth=1.5, zorder=6))
    ax.text(x + w/2, y + h * 0.66, label_main, ha='center', va='center',
            fontsize=fontsize_main, weight='bold', color=ec, zorder=7)
    ax.text(x + w/2, y + h * 0.28, label_sub, ha='center', va='center',
            fontsize=fontsize_sub, color=ec, zorder=7)


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
# Schematic 1: RMC
# =====================================================================
def schematic_rmc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(11, 10.7,
            'C. Proposed mechanism — RMC chemokine axis and framework-novel drug-class candidates',
            ha='center', va='center', fontsize=11, weight='bold')

    # --- RMC cell ---
    rmc_cx, rmc_cy, rmc_rx, rmc_ry = 4.5, 5.5, 3.0, 2.2
    ax.add_patch(Polygon(cell_outline_smooth(rmc_cx, rmc_cy, rmc_rx, rmc_ry),
                          closed=True, facecolor='#f8d7da', edgecolor='#922b21',
                          linewidth=2.0, alpha=0.9, zorder=2))
    ax.text(rmc_cx, rmc_cy + 3.0, 'SMARCB1-null RMC tumor cell',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#922b21', style='italic')

    # Nucleus + SMARCB1-X
    ax.add_patch(Ellipse((rmc_cx - 0.7, rmc_cy - 0.2), 1.8, 1.2,
                          facecolor='#cfd8e8', edgecolor='#1f3a5c',
                          linewidth=1.2, zorder=3))
    ax.text(rmc_cx - 0.7, rmc_cy + 0.15, 'Nucleus', ha='center', va='center',
            fontsize=7.5, style='italic', color='#1f3a5c', zorder=4)
    ax.text(rmc_cx - 0.7, rmc_cy - 0.40, 'SMARCB1', ha='center', va='center',
            fontsize=8.5, weight='bold', color='#1f3a5c', zorder=4)
    ax.plot([rmc_cx - 1.5, rmc_cx + 0.1], [rmc_cy + 0.05, rmc_cy - 0.75],
            color='#c00', lw=2.4, zorder=5)
    ax.plot([rmc_cx - 1.5, rmc_cx + 0.1], [rmc_cy - 0.75, rmc_cy + 0.05],
            color='#c00', lw=2.4, zorder=5)

    # CEACAM1 receptor — placed at angle 0 (east) on membrane
    ceacam_x, ceacam_y = membrane_point(rmc_cx, rmc_cy, rmc_rx, rmc_ry, 0)
    draw_receptor(ax, ceacam_x, ceacam_y, size=0.32, color='#7a4a00', angle=0,
                  lw=2.0)
    ax.text(ceacam_x + 0.55, ceacam_y - 0.55, 'CEACAM1',
            fontsize=8.5, weight='bold', color='#7a4a00', zorder=7)

    # Chemokine vesicles emanating from cell (between RMC and myeloid)
    chemokines = [
        (6.2, 7.0, 'IL-8'),
        (6.2, 5.5, 'CXCL1'),
        (6.2, 4.0, 'CXCL2'),
    ]
    for cx, cy, lbl in chemokines:
        ax.add_patch(Circle((cx, cy), 0.18, facecolor='#c00', edgecolor='black',
                             linewidth=0.6, alpha=0.9, zorder=5))
        ax.text(cx, cy + 0.50, lbl, ha='center', va='center',
                fontsize=7.5, weight='bold', color='#c00', zorder=7)
    # Secretion flow arrows (chemokine to myeloid receptor zone)
    for sy_start, sy_end in [(7.0, 6.5), (5.5, 5.5), (4.0, 4.5)]:
        ax.annotate('', xy=(10.4, sy_end), xytext=(6.5, sy_start),
                    arrowprops=dict(arrowstyle='->', lw=1.4,
                                    color='#c00', alpha=0.65))

    # --- Myeloid cell ---
    my_cx, my_cy, my_rx, my_ry = 14.5, 5.5, 2.7, 2.1
    ax.add_patch(Polygon(cell_outline_smooth(my_cx, my_cy, my_rx, my_ry),
                          closed=True, facecolor='#fff3cd', edgecolor='#806600',
                          linewidth=2.0, alpha=0.9, zorder=2))
    ax.text(my_cx, my_cy + 2.9, 'Myeloid cell (MDSC precursor)',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#806600', style='italic')
    ax.add_patch(Ellipse((my_cx, my_cy - 0.3), 1.4, 1.0,
                          facecolor='#cfd8e8', edgecolor='#1f3a5c',
                          linewidth=1.0, alpha=0.7, zorder=3))

    # CXCR1 at angle ~155 (upper-left), CXCR2 at angle ~205 (lower-left)
    cxcr1_x, cxcr1_y = membrane_point(my_cx, my_cy, my_rx, my_ry, 155)
    cxcr2_x, cxcr2_y = membrane_point(my_cx, my_cy, my_rx, my_ry, 205)
    draw_receptor(ax, cxcr1_x, cxcr1_y, size=0.32, color='#1d4d33', angle=155,
                  lw=2.0)
    draw_receptor(ax, cxcr2_x, cxcr2_y, size=0.32, color='#1d4d33', angle=205,
                  lw=2.0)
    ax.text(cxcr1_x - 0.30, cxcr1_y + 0.45, 'CXCR1', ha='right', va='center',
            fontsize=8.5, weight='bold', color='#1d4d33', zorder=7)
    ax.text(cxcr2_x - 0.30, cxcr2_y - 0.45, 'CXCR2', ha='right', va='center',
            fontsize=8.5, weight='bold', color='#1d4d33', zorder=7)

    # --- Drug boxes ---
    # CM24 (top-left, anti-CEACAM1)
    draw_drug_box(ax, 0.5, 9.0, 5.5, 1.0,
                  'FRAMEWORK-NOVEL: anti-CEACAM1',
                  'CM24 (Phase I/II)')
    # CXCR1/CXCR2 antagonists (top-right)
    draw_drug_box(ax, 11.5, 9.0, 9.5, 1.0,
                  'FRAMEWORK-NOVEL: CXCR1 / CXCR2 antagonists',
                  'reparixin · navarixin (MK-7123) · AZD5069 · danirixin · ladarixin',
                  fontsize_sub=7.0)

    # CM24 inhibition arrow: from CM24 box (3.25, 9.0) down + right to CEACAM1
    # Route around the cell so it doesn't cut through chemokines
    # Use a curved arrow via a midpoint above the cell, then down to CEACAM1
    draw_inhibition(ax, (5.5, 9.0), (ceacam_x + 0.05, ceacam_y + 0.10),
                    color='darkred', lw=2.0)

    # CXCR1/CXCR2 antagonist arrows from top box down to receptors
    draw_inhibition(ax, (13.5, 9.0), (cxcr1_x + 0.10, cxcr1_y + 0.15),
                    color='darkred', lw=2.0)
    draw_inhibition(ax, (15.5, 9.0), (cxcr2_x + 0.10, cxcr2_y - 0.15),
                    color='darkred', lw=2.0)

    # --- Output phenotype boxes (right side) ---
    draw_phenotype_box(ax, 17.8, 5.7, 4.0, 2.0,
                       'MDSC recruitment',
                       '+ immunosuppressive\ntumor microenvironment',
                       accent='#806600')
    draw_phenotype_box(ax, 17.8, 2.7, 4.0, 2.0,
                       'Tumor growth +',
                       'reduced anti-tumor\nimmunity',
                       accent='#7a1a00')
    # Connect myeloid cell to MDSC output, then MDSC -> tumor growth
    ax.annotate('', xy=(17.8, 6.4), xytext=(my_cx + my_rx + 0.1, 5.5),
                arrowprops=dict(arrowstyle='->', lw=1.6, color='#806600'))
    ax.annotate('', xy=(19.8, 4.7), xytext=(19.8, 5.7),
                arrowprops=dict(arrowstyle='->', lw=1.6, color='#7a1a00'))

    # --- Legend stripe at bottom ---
    ax.add_patch(FancyBboxPatch((0.2, 0.15), 21.6, 0.55,
                                 boxstyle="round,pad=0.04",
                                 ec='#888', fc='#f4f4f4', linewidth=0.8))
    ax.text(11, 0.42,
            '⊥ = drug inhibition  ·  Y = membrane receptor  ·  ● = secreted chemokine  ·  red = framework-novel target',
            ha='center', va='center', fontsize=8, style='italic', color='#333')


# =====================================================================
# Schematic 2: Sarc-UC
# =====================================================================
def schematic_sarcuc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(11, 10.7,
            'C. Proposed mechanism — Sarcomatoid UC framework-novel targets + TROP2-low negative biomarker',
            ha='center', va='center', fontsize=11, weight='bold')

    # --- Sarc-UC cell (large, centered) ---
    sc_cx, sc_cy, sc_rx, sc_ry = 11, 5.2, 5.0, 3.2
    ax.add_patch(Polygon(cell_outline_smooth(sc_cx, sc_cy, sc_rx, sc_ry),
                          closed=True, facecolor='#e8d8e8', edgecolor='#6c3483',
                          linewidth=2.0, alpha=0.9, zorder=2))
    ax.text(sc_cx, sc_cy + 3.85, 'Sarcomatoid urothelial carcinoma cell',
            ha='center', va='center', fontsize=10.5, weight='bold',
            color='#6c3483', style='italic')

    # Nucleus (larger now, gives targets more breathing room)
    ax.add_patch(Ellipse((sc_cx - 0.5, sc_cy + 0.5), 5.8, 2.0,
                          facecolor='#cfd8e8', edgecolor='#1f3a5c',
                          linewidth=1.2, zorder=3))
    ax.text(sc_cx - 0.5, sc_cy + 1.5, 'Nucleus', ha='center', va='center',
            fontsize=8, style='italic', color='#1f3a5c', zorder=4)
    # Nuclear targets spread out horizontally
    ax.add_patch(Circle((sc_cx - 2.7, sc_cy + 0.4), 0.45,
                         facecolor='#fadbd8', ec='#922b21', lw=1.2, zorder=4))
    ax.text(sc_cx - 2.7, sc_cy + 0.4, 'NSD2', ha='center', va='center',
            fontsize=7.5, weight='bold', color='#922b21', zorder=5)
    ax.add_patch(Circle((sc_cx - 0.5, sc_cy + 0.4), 0.45,
                         facecolor='#fadbd8', ec='#922b21', lw=1.2, zorder=4))
    ax.text(sc_cx - 0.5, sc_cy + 0.4, 'UHRF1', ha='center', va='center',
            fontsize=7.5, weight='bold', color='#922b21', zorder=5)
    ax.add_patch(Ellipse((sc_cx + 1.8, sc_cy + 0.4), 1.4, 0.6,
                          facecolor='#fadbd8', ec='#922b21', lw=1.2, zorder=4))
    ax.text(sc_cx + 1.8, sc_cy + 0.4, 'ATR-ATRIP', ha='center', va='center',
            fontsize=7.5, weight='bold', color='#922b21', zorder=5)
    ax.text(sc_cx - 0.5, sc_cy - 0.30,
            'Epigenetic dysregulation  +  DNA damage response',
            ha='center', va='center', fontsize=7.3, style='italic',
            color='#1f3a5c', zorder=5)

    # Cytoplasm: G6PD enzyme positioned bottom-right of cell
    ax.add_patch(Circle((sc_cx + 3.5, sc_cy - 1.8), 0.50,
                         facecolor='#fce5cd', ec='#a04a00', lw=1.3, zorder=4))
    ax.text(sc_cx + 3.5, sc_cy - 1.8, 'G6PD', ha='center', va='center',
            fontsize=7.5, weight='bold', color='#a04a00', zorder=5)
    ax.text(sc_cx + 3.5, sc_cy - 2.5, 'pentose phosphate\npathway',
            ha='center', va='center', fontsize=6.8, style='italic',
            color='#a04a00', zorder=5)

    # TROP2 receptor at angle 180 (west) on membrane
    trop2_x, trop2_y = membrane_point(sc_cx, sc_cy, sc_rx, sc_ry, 180)
    draw_receptor(ax, trop2_x, trop2_y, size=0.40, color='#1d3a8a', angle=180,
                  lw=2.2)
    ax.text(trop2_x - 0.55, trop2_y + 0.65, 'TROP2',
            ha='right', va='center', fontsize=9, weight='bold',
            color='#1d3a8a', zorder=7)
    ax.text(trop2_x - 0.55, trop2_y + 0.30, '(LOW)',
            ha='right', va='center', fontsize=7.5, weight='bold',
            color='#c00', style='italic', zorder=7)

    # --- Drug boxes around the cell ---
    # KTX-1001 → NSD2 (top-left, above cell)
    draw_drug_box(ax, 0.3, 8.9, 5.5, 1.0,
                  'FRAMEWORK-NOVEL: NSD2 inhibitor',
                  'KTX-1001 (Phase I)',
                  fontsize_main=7.8)
    # ATR inhibitors (top-right, above cell)
    draw_drug_box(ax, 13.5, 8.9, 8.0, 1.0,
                  'FRAMEWORK-NOVEL: ATR inhibitors',
                  'ceralasertib · berzosertib · elimusertib',
                  fontsize_main=7.8, fontsize_sub=7.0)
    # UHRF1 PROTAC (right margin, mid; placed beyond cell x=16)
    draw_drug_box(ax, 16.3, 6.2, 5.4, 0.9,
                  'PARTIALLY NOVEL: UHRF1 PROTAC',
                  'UM-002 (preclinical)',
                  fontsize_main=7.8)
    # G6PD inhibitor (right margin, bottom)
    draw_drug_box(ax, 16.3, 2.3, 5.4, 0.9,
                  'PARTIALLY NOVEL: G6PD inhibitor',
                  '6-aminonicotinamide',
                  fontsize_main=7.8)

    # Inhibition arrows updated to match new box positions
    draw_inhibition(ax, (3.0, 8.9), (sc_cx - 2.7, sc_cy + 0.85),
                    color='darkred', lw=2.0)
    draw_inhibition(ax, (17.5, 8.9), (sc_cx + 1.8, sc_cy + 0.85),
                    color='darkred', lw=2.0)
    draw_inhibition(ax, (16.3, 6.65), (sc_cx - 0.05, sc_cy + 0.55),
                    color='darkred', lw=2.0)
    draw_inhibition(ax, (16.3, 2.75), (sc_cx + 4.0, sc_cy - 1.8),
                    color='darkred', lw=2.0)

    # Negative biomarker box (bottom-left)
    ax.add_patch(FancyBboxPatch((0.5, 2.3), 5.5, 1.0,
                                  boxstyle="round,pad=0.05",
                                  ec='#1d3a8a', fc='#d6e4f0', linewidth=1.7,
                                  zorder=6))
    ax.text(3.25, 2.95, 'NEGATIVE BIOMARKER',
            ha='center', va='center', fontsize=8.8, weight='bold',
            color='#1d3a8a', zorder=7)
    ax.text(3.25, 2.55, 'sacituzumab govitecan → predicted non-response',
            ha='center', va='center', fontsize=7.3, color='#1d3a8a', zorder=7)
    # Dashed arrow with X (non-response) from negative biomarker box to TROP2
    ax.annotate('', xy=(trop2_x - 0.05, trop2_y), xytext=(3.25, 3.3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#1d3a8a',
                                linestyle='dashed'))
    # Red X over the TROP2 receptor showing non-response
    ax.plot([trop2_x - 0.55, trop2_x + 0.15],
            [trop2_y - 0.35, trop2_y + 0.35],
            color='#c00', lw=2.5, zorder=10)
    ax.plot([trop2_x - 0.55, trop2_x + 0.15],
            [trop2_y + 0.35, trop2_y - 0.35],
            color='#c00', lw=2.5, zorder=10)

    # --- Output phenotype boxes (bottom strip) ---
    draw_phenotype_box(ax, 0.5, 0.4, 6.8, 1.4,
                       'Epigenetic dysregulation reversal',
                       '+ DNA damage repair vulnerability',
                       accent='#922b21')
    draw_phenotype_box(ax, 7.7, 0.4, 6.5, 1.4,
                       'Metabolic reprogramming',
                       'pentose phosphate pathway',
                       accent='#a04a00')
    draw_phenotype_box(ax, 14.6, 0.4, 7.0, 1.4,
                       'TROP2-low → de-prioritize sacituzumab',
                       '(predicted non-response)',
                       accent='#1d3a8a')


# =====================================================================
# Schematic 3: SCBC (two cells side by side)
# =====================================================================
def schematic_scbc(ax):
    ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis('off')
    ax.text(11, 10.7,
            'C. Proposed mechanism — Lineage-stratified SCBC framework-novel cell-surface targets',
            ha='center', va='center', fontsize=11, weight='bold')

    # --- ASCL1+ cell (left) ---
    a_cx, a_cy, a_rx, a_ry = 5.5, 5.2, 3.0, 2.4
    ax.add_patch(Polygon(cell_outline_smooth(a_cx, a_cy, a_rx, a_ry),
                          closed=True, facecolor='#cfe0f5', edgecolor='#1f4e79',
                          linewidth=2.0, alpha=0.9, zorder=2))
    ax.text(a_cx, a_cy + 3.1, 'ASCL1-positive SCBC cell',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#1f4e79', style='italic')
    ax.add_patch(Ellipse((a_cx, a_cy), 1.6, 1.0, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.0, alpha=0.7,
                          zorder=3))
    ax.text(a_cx, a_cy, 'ASCL1+', ha='center', va='center',
            fontsize=8.5, weight='bold', color='#1f3a5c', zorder=4)

    # CEACAM5 receptors on RIGHT membrane of ASCL1+ cell (angles 350, 10, 30)
    ascl_recs = []
    for ang in [340, 10, 35]:
        rx_, ry_ = membrane_point(a_cx, a_cy, a_rx, a_ry, ang)
        draw_receptor(ax, rx_, ry_, size=0.30, color='#922b21', angle=ang,
                      lw=2.0)
        ascl_recs.append((rx_, ry_, ang))
    # Label
    ax.text(ascl_recs[1][0] + 0.6, ascl_recs[1][1] + 0.05, 'CEACAM5\n(HIGH)',
            fontsize=8.5, weight='bold', color='#922b21', zorder=7,
            ha='left', va='center')

    # --- NEUROD1+ cell (right) ---
    n_cx, n_cy, n_rx, n_ry = 16.5, 5.2, 3.0, 2.4
    ax.add_patch(Polygon(cell_outline_smooth(n_cx, n_cy, n_rx, n_ry),
                          closed=True, facecolor='#e6e0f5', edgecolor='#6c3483',
                          linewidth=2.0, alpha=0.9, zorder=2))
    ax.text(n_cx, n_cy + 3.1, 'NEUROD1-positive SCBC cell',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#6c3483', style='italic')
    ax.add_patch(Ellipse((n_cx, n_cy), 1.7, 1.0, facecolor='#cfd8e8',
                          edgecolor='#1f3a5c', linewidth=1.0, alpha=0.7,
                          zorder=3))
    ax.text(n_cx, n_cy, 'NEUROD1+', ha='center', va='center',
            fontsize=8.5, weight='bold', color='#1f3a5c', zorder=4)

    # SSTR2 receptors on LEFT membrane of NEUROD1+ cell (angles 145, 180, 210)
    neur_recs = []
    for ang in [145, 180, 215]:
        rx_, ry_ = membrane_point(n_cx, n_cy, n_rx, n_ry, ang)
        draw_receptor(ax, rx_, ry_, size=0.30, color='#6c3483', angle=ang,
                      lw=2.0)
        neur_recs.append((rx_, ry_, ang))
    ax.text(neur_recs[1][0] - 0.6, neur_recs[1][1] + 0.05, 'SSTR2\n(HIGH)',
            fontsize=8.5, weight='bold', color='#6c3483', zorder=7,
            ha='right', va='center')

    # --- Drug boxes top ---
    # ADC label shortened ("antibody-drug conjugate" -> "ADC") + smaller font
    # so the FRAMEWORK-NOVEL header text fits inside the box
    draw_drug_box(ax, 0.5, 9.0, 9.5, 1.0,
                  'FRAMEWORK-NOVEL: anti-CEACAM5 ADC',
                  '(tusamitamab ravtansine = prior proof-of-concept, '
                  'discontinued Dec 2023; replacement-agent required)',
                  fontsize_main=7.8, fontsize_sub=6.8)
    draw_drug_box(ax, 12.0, 9.0, 9.5, 1.0,
                  'FRAMEWORK-NOVEL: ¹⁷⁷Lu DOTATATE (FDA-approved)',
                  'theranostic — Ga-68 DOTATATE PET selection → ¹⁷⁷Lu therapy',
                  fontsize_main=7.8, fontsize_sub=6.8)

    # CEACAM5 inhibition arrows: ONE T-bar per receptor, all originating from
    # the drug box. To avoid the "tangle" look, draw them with consistent
    # angles and short, clean shafts.
    for rx_, ry_, _ in ascl_recs:
        draw_inhibition(ax, (5.25, 9.0), (rx_ + 0.05, ry_ + 0.05),
                        color='darkred', lw=1.6, bar_half=0.16)
    # SSTR2 binding arrows (theranostic): use directed arrows (not T-bars)
    # to indicate binding/delivery, not inhibition
    for rx_, ry_, _ in neur_recs:
        ax.annotate('', xy=(rx_ - 0.05, ry_ + 0.05), xytext=(16.75, 9.0),
                    arrowprops=dict(arrowstyle='-|>', lw=1.6,
                                    color='#6c3483'))

    # Radiation starburst near NEUROD1+ cell (larger, more prominent)
    rad_cx, rad_cy = 19.5, 5.0
    for ang in np.linspace(0, 2*np.pi, 12, endpoint=False):
        ax.plot([rad_cx + 0.20*np.cos(ang), rad_cx + 0.55*np.cos(ang)],
                [rad_cy + 0.20*np.sin(ang), rad_cy + 0.55*np.sin(ang)],
                color='#c00', lw=1.8, alpha=0.85)
    ax.add_patch(Circle((rad_cx, rad_cy), 0.20,
                         facecolor='#c00', edgecolor='black',
                         linewidth=0.8, alpha=0.6, zorder=6))
    ax.text(rad_cx, rad_cy - 1.05, '¹⁷⁷Lu radiation\nlocal cytotoxicity',
            ha='center', va='center', fontsize=7.5, color='#c00',
            weight='bold', style='italic')

    # ADC payload label — anchored INSIDE the ASCL1+ cell so it doesn't float
    ax.text(a_cx + 1.2, a_cy - 1.5, 'ADC payload\n→ apoptosis',
            ha='center', va='center', fontsize=7.5, color='#922b21',
            weight='bold', style='italic', zorder=4)

    # --- Output phenotype boxes ---
    draw_phenotype_box(ax, 0.5, 0.4, 10.0, 1.5,
                       'ASCL1-driven CEACAM5-mediated cytotoxicity',
                       'paradigm transfer from small-cell lung cancer',
                       accent='#1f4e79')
    draw_phenotype_box(ax, 11.5, 0.4, 10.0, 1.5,
                       'NEUROD1-driven peptide receptor radionuclide therapy',
                       'existing Ga-68 / Lu-177 theranostic infrastructure',
                       accent='#6c3483')


# =====================================================================
# Figure 2 — RMC
# =====================================================================
print("Generating Figure 2: RMC (refined schematic)")
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
                       height_ratios=[1.0, 1.20],
                       hspace=0.42, wspace=0.45,
                       left=0.08, right=0.97, top=0.94, bottom=0.04)
axA = fig.add_subplot(gs[0, 0])
axB = fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])

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

schematic_rmc(axC)

plt.suptitle('Figure 2. Renal Medullary Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.985)
plt.savefig(FIGURES / 'Figure2_RMC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure2_RMC.png ({(FIGURES/'Figure2_RMC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 3 — Sarc-UC
# =====================================================================
print("\nGenerating Figure 3: Sarc-UC (refined schematic)")
sarc_de = pd.read_csv(RESULTS / 'SarcomatoidUC_DE_full.csv')

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.20],
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

schematic_sarcuc(axC)

plt.suptitle('Figure 3. Sarcomatoid Urothelial Carcinoma — Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure3_SarcUC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure3_SarcUC.png ({(FIGURES/'Figure3_SarcUC.png').stat().st_size:,} bytes)")


# =====================================================================
# Figure 4 — SCBC
# =====================================================================
print("\nGenerating Figure 4: SCBC (refined schematic)")
scbc_subtypes = pd.read_csv(RESULTS / 'SCBC_subtype_calls.csv')
ascl1_df = pd.read_csv(RESULTS / 'SCBC_up_in_ASCL1.csv').head(10)
neur_df  = pd.read_csv(RESULTS / 'SCBC_up_in_NEUROD1.csv').head(10)

fig = plt.figure(figsize=(11, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig,
                       height_ratios=[1.0, 1.20],
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

# Panel B — clean combined headline bars, simpler layout
# Build dataframe with subtype labels embedded
ascl1_top = ascl1_df.head(8).copy()
ascl1_top['subtype'] = 'ASCL1+'
neur_top  = neur_df.head(8).copy()
neur_top['subtype'] = 'NEUROD1+'
# Group rows: ASCL1+ on TOP (gap), NEUROD1+ on BOTTOM
n_neur, n_ascl = len(neur_top), len(ascl1_top)
gap = 1.5
neur_y = np.arange(n_neur)[::-1] + 0.5
ascl_y = np.arange(n_ascl)[::-1] + 0.5 + n_neur + gap

# Plot ASCL1+ bars
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
# Subtype section dividers using axhline + text annotation in plot coords
divider_y = n_neur + gap / 2
axB.axhline(divider_y, color='#888', lw=0.6, alpha=0.5)
# Headline-target chip annotations in upper-right of each section
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

schematic_scbc(axC)

plt.suptitle('Figure 4. Small-Cell Bladder Cancer — Lineage-Stratified Framework-Novel Findings',
             fontsize=12, weight='bold', y=0.99)
plt.savefig(FIGURES / 'Figure4_SCBC.png', bbox_inches='tight')
plt.close()
print(f"  Saved Figure4_SCBC.png ({(FIGURES/'Figure4_SCBC.png').stat().st_size:,} bytes)")

print("\nAll three figures regenerated with refined schematics.")
