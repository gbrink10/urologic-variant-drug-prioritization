"""Figure 4 - every candidate without a prior proposal, against every criterion.

All six candidates are shown. The criteria rank them into a priority tier and a
lower-confidence tier; none is removed from the figure or from the paper, so a
reader can see the evidence behind each one and disagree with the ordering.

Three things change from v28:

  * the columns follow the stated selection criteria, so the reader can see
    which criterion each candidate failed rather than being told a count;
  * every cell carries a symbol as well as a colour (+ supports, ~ partial,
    - contradicts, n/a cannot test), so the figure survives red-green colour
    vision deficiency and greyscale printing;
  * the values come from the refit, and the enrichment column is only credited
    when the target is itself a member of the enriched pathway.

Writes: figures/Figure4_candidate_selection.png
"""
import sys
from pathlib import Path

import paths

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
FIG = paths.FIGURES
plt.rcParams.update({'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
                     'font.family': 'sans-serif'})

sel = pd.read_csv(RF / 'CANDIDATE_SELECTION.csv')
prov = pd.read_csv(RF / 'SCORING_PROVENANCE_V29.csv')
master = pd.read_csv(RF / 'MASTER_TABLE_V29.csv')
n_assoc = len(master)

SUPPORT, PARTIAL, AGAINST, UNTESTED = '#1e8449', '#f4d03f', '#c0392b', '#bdc3c7'
SYM = {SUPPORT: '+', PARTIAL: '~', AGAINST: '\u2212', UNTESTED: 'n/a'}

NAMES = {
    17: 'CXCR1/CXCR2 antagonists\n(renal medullary carcinoma)',
    19: 'Anti-CEACAM1 (CM24)\n(renal medullary carcinoma)',
    28: 'Anti-CEACAM5 conjugates\n(ASCL1+ small-cell bladder)',
    23: 'NSD2 inhibition (KTX-1001)\n(sarcomatoid urothelial)',
    24: 'ATR inhibition\n(sarcomatoid urothelial)',
    29: '$^{177}$Lu-DOTATATE\n(NEUROD1+ small-cell bladder)',
}
COLS = ['Transcriptomic\nevidence', 'Score', 'Meets its arm\'s\nstandard',
        'Target in\nenriched pathway', 'Protein\naccess',
        'Independent\nchecks', 'Clinical access /\ndevelopment path']

sel = sel.sort_values(['survives', 'total'], ascending=[False, False])
if 'pathway_estimable' not in sel.columns:
    sel['pathway_estimable'] = True
grid, notes, rows_lbl = [], [], []
for _, r in sel.iterrows():
    n = int(r['N'])
    p = prov[prov['N'] == n].iloc[0]
    cells, txt = [], []

    # which arm the transcriptomic evidence comes from, and whether the
    # pathway component could be computed at all for this context
    path_ok = bool(r.get('pathway_estimable', True))
    denom = int(r.get('total_denominator', 9) or 9)
    arm_abundance = pd.isna(r['E_refit_q'])
    cells.append(PARTIAL if arm_abundance else SUPPORT)
    txt.append('abundance\n(no contrast)' if arm_abundance else 'disease\ncontrast')

    if True:
        total = int(r['total'])
        cells.append(SUPPORT if total >= 7 else PARTIAL if total >= 4 else AGAINST)
        txt.append(f'{total}/{denom}')

        q = float(r['E_refit_q']) if pd.notna(r['E_refit_q']) else np.nan
        if np.isnan(q):
            e_pts = int(p['E_refit']) if pd.notna(p['E_refit']) else 0
            cells.append(SUPPORT if e_pts >= 2 else AGAINST)
            txt.append(f'top {"5%" if e_pts >= 3 else "15%" if e_pts == 2 else "third or below"}'
                       if e_pts else 'below\ntop third')
        elif q < 0.05:
            cells.append(SUPPORT)
            txt.append(f'q={q:.0e}' if q < 1e-3 else f'q={q:.3f}')
        else:
            cells.append(AGAINST); txt.append(f'q={q:.2f}')

        if not path_ok:
            cells.append(UNTESTED)
            txt.append('not estimable\n(confounded\ncontrast)')
        elif bool(r['target_in_enriched_pathway']):
            cells.append(SUPPORT); txt.append(f"q={float(r['pathway_q']):.3f}")
        elif pd.notna(r['pathway_q']) and float(r['pathway_q']) < 0.10:
            # the pathway is enriched but the target is not driving it
            cells.append(PARTIAL); txt.append('other\ngenes')
        elif pd.notna(r['pathway_q']):
            # the target sits in a pre-specified set that is not enriched
            cells.append(AGAINST); txt.append('set not\nenriched')
        else:
            cells.append(UNTESTED); txt.append('not in\npanel')

    pl = str(r['protein_layer'])
    if 'confirmed' in pl:
        cells.append(SUPPORT); txt.append('membrane')
    elif 'intracellular' in pl:
        cells.append(UNTESTED); txt.append('n/a\nintracell.')
    else:
        cells.append(UNTESTED); txt.append('n/a')

    # the dependency and compound screens are one column: for five of the six
    # rows neither screen can speak to the candidate at all
    dl, cl = str(r['dependency_layer']), str(r['compound_layer'])
    if dl.startswith('no dependency'):
        cells.append(AGAINST); txt.append('no CRISPR\ndependency')
    elif 'not selective' in dl or 'active but not selective' in cl:
        cells.append(PARTIAL)
        txt.append('pan-essential;\nnot selective')
    else:
        cells.append(UNTESTED); txt.append('cannot\ntest')

    if 'E4' in str(r['failed_criteria']):
        cells.append(AGAINST); txt.append('discontinued')
    else:
        cells.append(SUPPORT); txt.append('clinical-\nstage')

    grid.append(cells); notes.append(txt); rows_lbl.append(NAMES.get(n, str(n)))

n_novel = len(sel)
n_surv = int(sel['survives'].sum())
n_ctx = int(sel[sel['survives']]['Context'].nunique())

fig = plt.figure(figsize=(9.6, 5.2))
axB = fig.add_subplot(111)
n_r, n_c = len(grid), len(COLS)
for i in range(n_r):
    for j in range(n_c):
        c = grid[i][j]
        axB.add_patch(plt.Rectangle((j, n_r - 1 - i), 1, 1, fc=c, ec='white',
                                    lw=2.0))
        dark = c in (SUPPORT, AGAINST)
        axB.text(j + 0.5, n_r - 1 - i + 0.68, SYM[c], ha='center', va='center',
                 fontsize=11, weight='bold',
                 color='white' if dark else '#2c3e50')
        axB.text(j + 0.5, n_r - 1 - i + 0.30, notes[i][j], ha='center',
                 va='center', fontsize=5.9,
                 color='white' if dark else '#2c3e50', weight='bold')
axB.set_xlim(0, n_c); axB.set_ylim(0, n_r)
axB.set_xticks([j + 0.5 for j in range(n_c)])
axB.set_xticklabels(COLS, fontsize=7.0)
axB.xaxis.set_ticks_position('top')
axB.set_yticks([n_r - 1 - i + 0.5 for i in range(n_r)])
axB.set_yticklabels(rows_lbl, fontsize=7.0)
for s in axB.spines.values():
    s.set_visible(False)
axB.tick_params(length=0)
# mark where the survivors stop
axB.axhline(n_r - n_surv, color='#1a1a1a', lw=1.6, ls='--')
axB.text(n_c + 0.06, n_r - n_surv, ' priority\n tier above', fontsize=6.6,
         va='center', style='italic', color='#1a1a1a')
axB.set_title(f'All {n_novel} candidates without a prior urologic-oncology '
              f'proposal, against every criterion', fontsize=10.2,
              weight='bold', pad=30, loc='left')

handles = [plt.Rectangle((0, 0), 1, 1, fc=c, ec='white')
           for c in (SUPPORT, PARTIAL, AGAINST, UNTESTED)]
labels = ['+  supports', '~  partial', '\u2212  contradicts', 'n/a  cannot test']
axB.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, -0.03),
           ncol=4, frameon=False, fontsize=7.4)

out = FIG / 'Figure4_candidate_selection.png'
plt.savefig(out, bbox_inches='tight')
plt.close()
print(f"Saved {out} ({out.stat().st_size:,} bytes)")
print(f"  {n_assoc} associations -> {n_novel} with no prior proposal, all shown: "
      f"{n_surv} priority in {n_ctx} diseases, {n_novel - n_surv} lower-confidence")
for _, r in sel.iterrows():
    print(f"    row {int(r['N']):<3} {r['priority_tier']:<17} "
          f"{r['reservation'][:58]}")
