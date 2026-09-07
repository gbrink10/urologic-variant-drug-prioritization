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
import matplotlib.image as mpimg
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
              f'genome-wide r = {r_p:.2f}',
              fontsize=9.3, weight='bold', loc='left')
axA.legend(loc='lower right', fontsize=7.2, frameon=False)
for s in ('top', 'right'):
    axA.spines[s].set_visible(False)

# ---------------- B: the chemokine axis, per line --------------------------
axB = fig.add_subplot(gs[0, 1])
# CEACAM1 is nominated separately and is in no enriched set, so it is
# separated from the four chemokine ligands by a gap rather than stacked with
# them under one pathway q-value
GAP = 0.9
ypos = np.array([(len(present) - 1 - _i)
                 + (0.0 if _g == 'CEACAM1' else GAP)
                 for _i, _g in enumerate(present)])
w = 0.38
axB.barh(ypos + w / 2, [d.loc[g, 'l2fc_disease_48h_2C'] for g in present],
         height=w, color='#1f4e79', label='RMC-2C')
axB.barh(ypos - w / 2, [d.loc[g, 'l2fc_disease_48h_219'] for g in present],
         height=w, color='#7fb3d5', label='RMC219')
axB.set_yticks(ypos)
axB.set_yticklabels([g if g != 'CEACAM1' else 'CEACAM1' for g in present],
                    fontsize=8.6)
axB.axvline(0, lw=0.8, c='#333')
axB.set_xlabel('log$_2$ fold change (higher in SMARCB1-null disease state)',
               fontsize=8.2)
axB.set_title('B. Nominated RMC signals, each line separately',
              fontsize=9.3, weight='bold', loc='left')
# annotate the two groups inside the axes, so the q-value is attached only to
# the ligands that actually drive the enrichment
_lig = [g for g in present if g != 'CEACAM1']
_xr = max(abs(d.loc[g, 'l2fc_disease_48h_2C']) for g in present) * 1.02
if _lig:
    _y = [ypos[present.index(g)] for g in _lig]
    axB.text(_xr, float(max(_y)) + 0.60,
             f'chemokine ligands of the enriched pathway (q = {chem_q:.4f})',
             ha='right', va='center', fontsize=6.8, style='italic',
             color='#1f4e79')
if 'CEACAM1' in present:
    axB.text(_xr, float(ypos[present.index('CEACAM1')]) + 0.60,
             'CEACAM1: nominated separately, in no enriched set',
             ha='right', va='center', fontsize=6.8, style='italic',
             color='#7d6608')
axB.set_ylim(-0.8, float(max(ypos)) + 1.15)
axB.legend(fontsize=7.4, frameon=False, loc='lower right')
for s in ('top', 'right'):
    axB.spines[s].set_visible(False)

# ---------------- C: mechanism schematic ------------------------------------
# Checked arrow by arrow before use: CXCL8 reaches both receptors, CXCL1/2/3
# reach CXCR2 only, and both receptors sit in the neutrophil membrane rather
# than on the tumor cell.
axC = fig.add_subplot(gs[0, 2])
axC.imshow(mpimg.imread(str(paths.PANEL_C / 'PanelC_RMC.png')))
axC.axis('off')
axC.set_title('C. Proposed mechanism and point of blockade', fontsize=9.3,
              weight='bold', loc='left')

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
