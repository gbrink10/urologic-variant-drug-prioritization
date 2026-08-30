"""Figures 3 and 4 (v29), rebuilt from the refit.

Figure 3 - sarcomatoid urothelial carcinoma
  A  volcano from the limma refit, key targets labelled
  B  pathway enrichment separating nominal from FDR-significant, which the v28
     panel conflated by colouring everything below nominal p < 0.10 red
  C  mechanism schematic

Figure 4 - lineage-stratified small-cell bladder cancer
  A  subtype composition
  B  the nominated target in each subtype, with its refit q-value, so the
     reader can see that the NEUROD1 branch no longer reaches significance
  C  mechanism schematic

The v28 Figure 4 was headed "framework-novel cell-surface targets", which was
wrong twice over: PTGS1/COX-1 is an intracellular enzyme, and the POU2F3-COX
association is partially novel rather than framework-novel. The heading is now
descriptive.

Writes: figures/Figure3_SarcUC.png, figures/Figure4_SCBC.png
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg
import numpy as np
import pandas as pd

import lib_symbols

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parents[2]
RF = REPO / 'results' / 'refit'
DEDIR = REPO / 'data' / 'DE_results'
FIG = Path(r"C:\Users\garre\framework_expansion\figures")
PANEL = FIG / 'panelC'
plt.rcParams.update({'figure.dpi': 200, 'savefig.dpi': 300, 'font.size': 9,
                     'font.family': 'sans-serif'})

enr = pd.read_csv(RF / 'KEGG_ENRICHMENT_REFIT.csv')
enr = enr[enr['rule'] == 'q<0.05 & logFC>0.5']

sarc_map = pd.read_csv(DEDIR / 'SarcomatoidUC_DE_full.csv.gz')
SARC = dict(zip(sarc_map['probe_id'].astype(str),
                sarc_map['gene'].astype(str).str.upper()))


def de(ctx, mapping=None):
    t = pd.read_csv(RF / f'DE_{ctx}.csv')
    sym = (t['gene'].astype(str).map(mapping) if mapping
           else t['gene'].astype(str).str.upper())
    t['symbol'] = lib_symbols.to_symbols(sym.fillna('')).values
    return t[t['symbol'] != ''].sort_values('P.Value').drop_duplicates('symbol')


def panel_c(ax, name, title):
    img = mpimg.imread(str(PANEL / name))
    ax.imshow(img)
    ax.axis('off')
    ax.set_title(title, fontsize=9.8, weight='bold', loc='left')


# =====================================================================
# Figure 3
# =====================================================================
d = de('SarcUC', SARC)
fig = plt.figure(figsize=(15.6, 5.2))
gs = gridspec.GridSpec(1, 3, width_ratios=[1.0, 1.0, 1.45], wspace=0.28,
                       left=0.05, right=0.99, top=0.84, bottom=0.13)

axA = fig.add_subplot(gs[0, 0])
x = d['logFC'].values
y = -np.log10(d['adj.P.Val'].clip(lower=1e-300).values)
axA.scatter(x, y, s=3, c='#d9d9d9', alpha=0.5, linewidths=0, rasterized=True)
sig = (d['adj.P.Val'] < 0.05) & (d['logFC'].abs() > 0.5)
axA.scatter(x[sig.values], y[sig.values], s=5, c='#c0392b', alpha=0.6,
            linewidths=0, label=f'q<0.05, |log$_2$FC|>0.5 (n={int(sig.sum()):,})')
LAB = {'NSD2': (8, 6), 'UHRF1': (8, -10), 'G6PD': (-40, 6), 'ATR': (10, 0),
       'TACSTD2': (-58, 4)}
for g, off in LAB.items():
    h = d[d['symbol'] == g]
    if not len(h):
        continue
    gx = float(h['logFC'].iloc[0])
    gy = -np.log10(max(float(h['adj.P.Val'].iloc[0]), 1e-300))
    axA.scatter([gx], [gy], s=48, facecolor='#1a3a5c', edgecolor='white',
                linewidth=1.0, zorder=5)
    axA.annotate(g, (gx, gy), textcoords='offset points', xytext=off,
                 fontsize=7.8, weight='bold', color='#1a3a5c', zorder=6)
axA.axvline(0, lw=0.7, c='#bbb')
axA.axhline(-np.log10(0.05), ls='--', lw=0.8, c='#888')
axA.set_xlabel('log$_2$ fold change (sarcomatoid vs conventional)', fontsize=8.4)
axA.set_ylabel('$-$log$_{10}$ q', fontsize=8.6)
axA.set_title('A. Differential expression (limma refit)\n'
              '28 sarcomatoid vs 84 conventional', fontsize=9.5,
              weight='bold', loc='left')
axA.legend(fontsize=7.0, frameon=False, loc='upper left')
for s_ in ('top', 'right'):
    axA.spines[s_].set_visible(False)

axB = fig.add_subplot(gs[0, 1])
e = enr[enr['context'] == 'SarcUC'].nsmallest(7, 'pvalue').iloc[::-1]
ypos = np.arange(len(e))
vals = -np.log10(e['pvalue'].clip(lower=1e-300))
fdr = e['qvalue_BH'] < 0.10
bars = axB.barh(ypos, vals, color=['#1e8449' if f else '#f4d03f' for f in fdr],
                edgecolor='#333', linewidth=0.6)
for i, (v, q, f) in enumerate(zip(vals, e['qvalue_BH'], fdr)):
    axB.text(v + 0.06, i, f'q={q:.3f}' + ('  *' if f else ''), va='center',
             fontsize=6.8, color='#1a1a1a')
axB.set_yticks(ypos)
axB.set_yticklabels([p.replace('_', ' ') for p in e['pathway']], fontsize=7.6)
axB.axvline(-np.log10(0.05), ls='--', lw=0.8, c='#888')
axB.set_xlabel('$-$log$_{10}$ nominal p', fontsize=8.4)
axB.set_xlim(0, float(vals.max()) * 1.32)
axB.set_title('B. Pathway enrichment\n'
              'green with * survives FDR (q<0.10); gold is nominal only',
              fontsize=9.5, weight='bold', loc='left')
for s_ in ('top', 'right'):
    axB.spines[s_].set_visible(False)

panel_c(fig.add_subplot(gs[0, 2]), 'PanelC_SarcUC.png',
        'C. Nominated targets by subcellular compartment')
out3 = FIG / 'Figure3_SarcUC.png'
plt.savefig(out3, bbox_inches='tight')
plt.close()
print(f"Saved {out3.name} ({out3.stat().st_size:,} bytes)")
print("  Figure 3 pathways:",
      [(r['pathway'], round(r['qvalue_BH'], 4)) for _, r in e.iloc[::-1].iterrows()][:4])

# =====================================================================
# Figure 4
# =====================================================================
meta = pd.read_csv(REPO / 'data' / 'prepared' / 'SCBC_meta.csv')
counts = meta['subtype'].value_counts()
SUBS = [('ASCL1', 'CEACAM5', 'SCBC_ASCL1'), ('NEUROD1', 'SSTR2', 'SCBC_NEUROD1'),
        ('POU2F3', 'PTGS1', 'SCBC_POU2F3'), ('YAP1', None, 'SCBC_YAP1')]

fig = plt.figure(figsize=(15.6, 5.2))
gs = gridspec.GridSpec(1, 3, width_ratios=[0.78, 1.05, 1.6], wspace=0.30,
                       left=0.05, right=0.99, top=0.84, bottom=0.13)

axA = fig.add_subplot(gs[0, 0])
order = [s for s, _, _ in SUBS if s in counts.index]
vals = [int(counts[s]) for s in order]
cols = ['#1f4e79', '#7fb3d5', '#b9770e', '#bdc3c7']
axA.bar(range(len(order)), vals, color=cols[:len(order)], edgecolor='#333',
        linewidth=0.7)
for i, v in enumerate(vals):
    axA.text(i, v + 0.4, str(v), ha='center', fontsize=8.4, weight='bold')
axA.set_xticks(range(len(order)))
axA.set_xticklabels([f'{s}+' for s in order], fontsize=8.2)
axA.set_ylabel('tumours', fontsize=8.6)
axA.set_ylim(0, max(vals) * 1.2)
axA.set_title(f'A. Lineage subtypes\nGSE269750, n = {int(sum(vals))}',
              fontsize=9.5, weight='bold', loc='left')
for s_ in ('top', 'right'):
    axA.spines[s_].set_visible(False)

axB = fig.add_subplot(gs[0, 1])
rows = []
for sub, gene, ctx in SUBS:
    if gene is None:
        continue
    t = de(ctx)
    h = t[t['symbol'] == gene]
    if len(h):
        rows.append((f'{gene}\nin {sub}+', float(h['logFC'].iloc[0]),
                     float(h['adj.P.Val'].iloc[0])))
ypos = np.arange(len(rows))[::-1]
cols_b = ['#1e8449' if q < 0.05 else '#c0392b' for _, _, q in rows]
axB.barh(ypos, [fc for _, fc, _ in rows], color=cols_b, edgecolor='#333',
         linewidth=0.6)
for yp, (_, fc, q) in zip(ypos, rows):
    axB.text(fc + 0.12, yp, f'q={q:.3g}', va='center', fontsize=7.2,
             color='#1a1a1a')
axB.set_yticks(ypos)
axB.set_yticklabels([lbl for lbl, _, _ in rows], fontsize=7.8)
axB.set_xlabel('log$_2$ fold change vs remaining subtypes', fontsize=8.4)
axB.set_xlim(0, max(fc for _, fc, _ in rows) * 1.35)
axB.set_title('B. Nominated target per subtype\n'
              'green q<0.05; red does not reach significance',
              fontsize=9.5, weight='bold', loc='left')
for s_ in ('top', 'right'):
    axB.spines[s_].set_visible(False)

panel_c(fig.add_subplot(gs[0, 2]), 'PanelC_SCBC.png',
        'C. Proposed lineage-stratified therapeutic hypotheses')
out4 = FIG / 'Figure4_SCBC.png'
plt.savefig(out4, bbox_inches='tight')
plt.close()
print(f"Saved {out4.name} ({out4.stat().st_size:,} bytes)")
for lbl, fc, q in rows:
    print(f"  {lbl.replace(chr(10), ' '):<22} log2FC {fc:+.2f}  q={q:.3g}")
