"""Figure 2 (v29) - renal medullary carcinoma, corrected for what the data are.

The v26-v28 figure showed a volcano plot of one cell line's 48-hour contrast and
labelled it "n=9", which reads as nine independent tumors. The experiment is two
patient-derived cell lines with SMARCB1 rescue, so the honest display is the
agreement between the two lines, which is also the actual evidence for the lead
candidate.

  A  effect in RMC-2C against effect in RMC219, every gene, chemokine axis
     highlighted - consistency between lines is the claim being made
  B  the chemokine axis gene by gene, both lines shown separately
  C  mechanism schematic, checked molecule by molecule before use

Writes: figures/Figure2_RMC.png
"""
import sys
from pathlib import Path

import paths

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Circle, Ellipse)

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
FIG = paths.FIGURES
plt.rcParams.update({'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
                     'font.family': 'sans-serif'})

d = pd.read_csv(RF / 'RMC_REANALYSIS.csv', index_col=0)
enr = pd.read_csv(RF / 'RMC_ENRICHMENT.csv')
chem_q = float(enr[(enr['analysis'] == 'both lines')
                   & (enr['pathway'] == 'Chemokine_signaling')]['qvalue_BH'].iloc[0])

AXIS = ['CXCL8', 'CXCL1', 'CXCL2', 'CXCL3', 'CEACAM1']
present = [g for g in AXIS if g in d.index]

fig = plt.figure(figsize=(15.6, 5.2))
gs = gridspec.GridSpec(1, 3, width_ratios=[1.0, 0.95, 1.45], wspace=0.30,
                       left=0.05, right=0.99, top=0.82, bottom=0.12)

# ---------------- A: agreement between the two cell lines ------------------
axA = fig.add_subplot(gs[0, 0])
x = d['l2fc_disease_48h_2C'].values
y = d['l2fc_disease_48h_219'].values
ok = np.isfinite(x) & np.isfinite(y)
axA.scatter(x[ok], y[ok], s=3, c='#d9d9d9', alpha=0.55, linewidths=0, rasterized=True)
both_up = d['up_both'].fillna(False).values & ok
axA.scatter(x[both_up], y[both_up], s=7, c='#c0392b', alpha=0.75, linewidths=0,
            label=f'up in both lines (n={int(both_up.sum()):,})')
LABEL_OFFSET = {'CXCL8': (9, 5), 'CXCL1': (11, -3), 'CXCL2': (-36, 9),
                'CXCL3': (9, -13), 'CEACAM1': (-56, -3)}
for g in present:
    r = d.loc[g]
    gx, gy = r['l2fc_disease_48h_2C'], r['l2fc_disease_48h_219']
    axA.scatter([gx], [gy], s=52, facecolor='#1a3a5c', edgecolor='white',
                linewidth=1.1, zorder=5)
    axA.annotate(g, (gx, gy), textcoords='offset points',
                 xytext=LABEL_OFFSET.get(g, (9, 5)), fontsize=8, weight='bold',
                 color='#1a3a5c', zorder=6)
lim = np.nanpercentile(np.abs(np.r_[x[ok], y[ok]]), 99.5)
axA.plot([-lim, lim], [-lim, lim], ls='--', lw=0.9, c='#888', zorder=1)
axA.axhline(0, lw=0.7, c='#bbb'); axA.axvline(0, lw=0.7, c='#bbb')
axA.set_xlim(-lim, lim); axA.set_ylim(-lim, lim)
r_p = np.corrcoef(x[ok], y[ok])[0, 1]
axA.set_xlabel('log$_2$ fold change, RMC-2C', fontsize=8.6)
axA.set_ylabel('log$_2$ fold change, RMC219', fontsize=8.6)
axA.set_title('A. The two patient-derived lines compared\n'
              f'genome-wide r = {r_p:.2f}; agreement is the exception',
              fontsize=9.3, weight='bold', loc='left')
axA.legend(loc='lower right', fontsize=7.2, frameon=False)
for s in ('top', 'right'):
    axA.spines[s].set_visible(False)

# ---------------- B: the chemokine axis, per line --------------------------
axB = fig.add_subplot(gs[0, 1])
ypos = np.arange(len(present))[::-1]
w = 0.38
axB.barh(ypos + w / 2, [d.loc[g, 'l2fc_disease_48h_2C'] for g in present],
         height=w, color='#1f4e79', label='RMC-2C')
axB.barh(ypos - w / 2, [d.loc[g, 'l2fc_disease_48h_219'] for g in present],
         height=w, color='#7fb3d5', label='RMC219')
axB.set_yticks(ypos); axB.set_yticklabels(present, fontsize=8.6)
axB.axvline(0, lw=0.8, c='#333')
axB.set_xlabel('log$_2$ fold change (higher in SMARCB1-null disease state)',
               fontsize=8.2)
axB.set_title('B. Chemokine axis, each line separately\n'
              f'pathway q = {chem_q:.4f} on the both-lines set',
              fontsize=9.3, weight='bold', loc='left')
axB.legend(fontsize=7.4, frameon=False, loc='lower right')
for s in ('top', 'right'):
    axB.spines[s].set_visible(False)

# ---------------- C: mechanism, drawn so the receptor map is explicit -------
# CXCL8 binds both CXCR1 and CXCR2; CXCL1, CXCL2 and CXCL3 are CXCR2-selective.
axC = fig.add_subplot(gs[0, 2])
axC.set_xlim(0, 10); axC.set_ylim(0, 10); axC.axis('off')
axC.set_title('C. Proposed mechanism and point of blockade', fontsize=9.3,
              weight='bold', loc='left', pad=12)

axC.add_patch(Ellipse((2.05, 6.9), 3.5, 3.5, facecolor='#eaf2f8',
                      edgecolor='#1f4e79', lw=1.4))
axC.text(2.05, 8.05, 'RMC tumor cell', ha='center', fontsize=8.2,
         weight='bold', color='#1f4e79')
axC.text(2.05, 7.55, 'SMARCB1 loss', ha='center', fontsize=7.5, style='italic',
         color='#c0392b')
LIG = [('CXCL8', 7.05, '#1a3a5c'), ('CXCL1', 6.55, '#2e86c1'),
       ('CXCL2', 6.05, '#2e86c1'), ('CXCL3', 5.55, '#2e86c1')]
for name, y, col in LIG:
    axC.text(2.05, y, name, ha='center', va='center', fontsize=7.4,
             weight='bold', color=col, family='monospace')

# neutrophil with the two receptors
axC.add_patch(Circle((7.9, 6.0), 1.75, facecolor='#fdf2e9', edgecolor='#b9770e',
                     lw=1.4))
axC.text(7.9, 8.05, 'neutrophil', ha='center', fontsize=8.2, weight='bold',
         color='#b9770e')
rec = {}
for lab, y in (('CXCR1', 6.85), ('CXCR2', 5.35)):
    px = 7.9 - 1.75 * 0.62
    axC.add_patch(Circle((px, y), 0.30, facecolor='#1a3a5c', edgecolor='white',
                         lw=1.1, zorder=6))
    axC.text(px + 0.42, y, lab, ha='left', va='center', fontsize=7.6,
             weight='bold', color='#1a3a5c', zorder=7)
    rec[lab] = (px, y)
axC.text(8.15, 5.9, 'myeloid\nrecruitment', ha='center', va='center',
         fontsize=7.2, color='#7e5109', style='italic')

# ligand -> receptor arrows, drawn one per real interaction
ARROWS = [('CXCL8', 'CXCR1', '#1a3a5c'), ('CXCL8', 'CXCR2', '#1a3a5c'),
          ('CXCL1', 'CXCR2', '#2e86c1'), ('CXCL2', 'CXCR2', '#2e86c1'),
          ('CXCL3', 'CXCR2', '#2e86c1')]
ly = {n: y for n, y, _ in LIG}
for lig, receptor, col in ARROWS:
    x0, y0 = 3.5, ly[lig]
    x1, y1 = rec[receptor]
    axC.add_patch(FancyArrowPatch((x0, y0), (x1 - 0.34, y1),
                                  connectionstyle='arc3,rad=0.16',
                                  arrowstyle='-|>', mutation_scale=9, lw=1.0,
                                  color=col, alpha=0.85))
axC.text(5.2, 7.75, 'CXCL8 binds both receptors;\nCXCL1/2/3 are CXCR2-selective',
         ha='center', fontsize=6.6, style='italic', color='#555')

# blockade
axC.add_patch(FancyBboxPatch((0.15, 1.75), 5.6, 1.35,
                             boxstyle='round,pad=0.10', facecolor='#e8f6ef',
                             edgecolor='#1e8449', lw=1.3))
axC.text(2.95, 2.70, 'CXCR1- and/or CXCR2 antagonists', ha='center',
         fontsize=8.0, weight='bold', color='#1e8449')
axC.text(2.95, 2.14, 'reparixin \u00b7 navarixin \u00b7 AZD5069 \u00b7 danirixin',
         ha='center', fontsize=6.9, color='#145a32')
for lab in ('CXCR1', 'CXCR2'):
    x1, y1 = rec[lab]
    axC.add_patch(FancyArrowPatch((5.75, 2.6), (x1 - 0.30, y1 - 0.34),
                                  connectionstyle='arc3,rad=-0.22',
                                  arrowstyle='-[', mutation_scale=7, lw=1.5,
                                  color='#1e8449'))
axC.text(5.0, 0.95,
         'The mechanism runs through the myeloid compartment, so a tumor-cell\n'
         'monoculture cannot test it in either direction.',
         ha='center', fontsize=6.9, style='italic', color='#555')

out = FIG / 'Figure2_RMC.png'
plt.savefig(out, bbox_inches='tight')
plt.close()
print(f"Saved {out} ({out.stat().st_size:,} bytes)")
print(f"  two-line correlation r = {r_p:.3f}")
print(f"  genes up in both lines = {int(both_up.sum()):,}")
print(f"  chemokine signalling q = {chem_q:.5f}")
for g in present:
    print(f"    {g:<9} RMC-2C {d.loc[g, 'l2fc_disease_48h_2C']:+.2f}   "
          f"RMC219 {d.loc[g, 'l2fc_disease_48h_219']:+.2f}")
